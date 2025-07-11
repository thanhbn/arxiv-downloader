#!/usr/bin/env python3
"""
Script dịch các file paper từ tiếng Anh sang tiếng Việt
Sử dụng OpenAI API để dịch thuật chuyên nghiệp
"""

import os
import glob
import openai
from pathlib import Path
import time
import json
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PaperTranslator:
    def __init__(self):
        # Lấy API key từ environment
        self.client = openai.OpenAI()
        self.base_dir = Path(".")
        os.chdir(self.base_dir)  # Change working directory to arxiv-downloader
        
        # Prompt dịch thuật chuyên nghiệp
        self.translation_prompt = """Bạn là một trợ lý dịch thuật chuyên nghiệp, có khả năng dịch văn bản học thuật và kỹ thuật một cách chính xác.

Nhiệm vụ của bạn là dịch toàn bộ nội dung sau sang tiếng Việt.

Tập trung vào việc:
1. Dịch thuật chính xác các thuật ngữ AI/ML và khoa học máy tính.
2. Giữ nguyên định dạng của văn bản gốc (URLs arXiv, DOI, v.v.).
3. Sử dụng văn phong học thuật, trang trọng.
4. Đảm bảo bản dịch mượt mà và dễ hiểu trong ngữ cảnh tiếng Việt.
5. Giữ nguyên các từ tiếng Anh trong ngoặc đơn sau thuật ngữ tiếng Việt nếu cần thiết.
6. Đặc biệt chú ý dịch đúng các chủ đề nghiên cứu AI như RAG, Chain-of-Thought, Multimodal, v.v.

Văn bản cần dịch:
"""

    def find_untranslated_files(self):
        """Tìm các file .txt chưa có bản dịch _vi.txt"""
        # Tìm trong thư mục hiện tại và các collection folders
        all_txt_files = []
        
        # Tìm files .txt trong thư mục gốc
        root_txt_files = glob.glob("*.txt")
        all_txt_files.extend(root_txt_files)
        
        # Tìm files arxiv_links.txt trong các collection folders
        collection_dirs = [d for d in os.listdir('.') if os.path.isdir(d) and not d.startswith('.')]
        for collection_dir in collection_dirs:
            links_file = os.path.join(collection_dir, "arxiv_links.txt")
            if os.path.exists(links_file):
                all_txt_files.append(links_file)
        
        untranslated = []
        for txt_file in all_txt_files:
            if not txt_file.endswith("_vi.txt"):
                vi_file = txt_file.replace(".txt", "_vi.txt")
                if not os.path.exists(vi_file):
                    untranslated.append(txt_file)
        
        return untranslated

    def read_file_content(self, file_path):
        """Đọc nội dung file với encoding UTF-8"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Thử encoding khác nếu UTF-8 không hoạt động
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()

    def translate_text_chunks(self, text, max_chunk_size=6000):
        """Chia text thành chunks nhỏ để dịch với chiến lược thông minh"""
        chunks = []
        current_chunk = ""
        
        paragraphs = text.split('\n\n')
        threshold_size = int(max_chunk_size * 1.5)  # 150% of max chunk size
        
        i = 0
        while i < len(paragraphs):
            paragraph = paragraphs[i]
            
            # Calculate remaining text size from current paragraph onwards
            remaining_text = '\n\n'.join(paragraphs[i:])
            current_plus_paragraph = current_chunk + paragraph
            
            # Check if adding this paragraph exceeds max_chunk_size
            if len(current_plus_paragraph) > max_chunk_size:
                if current_chunk:
                    # Smart decision: if remaining text (including current paragraph) is < 150% of max_chunk_size,
                    # include everything in current chunk instead of creating a small leftover chunk
                    if len(current_chunk + remaining_text) <= threshold_size:
                        current_chunk += remaining_text
                        chunks.append(current_chunk.strip())
                        break  # All remaining text processed
                    else:
                        chunks.append(current_chunk.strip())
                        current_chunk = paragraph + "\n\n"
                else:
                    # Paragraph quá dài, chia nhỏ hơn
                    sentences = paragraph.split('. ')
                    j = 0
                    while j < len(sentences):
                        sentence = sentences[j]
                        remaining_sentences = '. '.join(sentences[j:])
                        current_plus_sentence = current_chunk + sentence
                        
                        if len(current_plus_sentence) > max_chunk_size:
                            if current_chunk:
                                # Smart decision for sentences too
                                if len(current_chunk + remaining_sentences) <= threshold_size:
                                    current_chunk += remaining_sentences
                                    j = len(sentences)  # Exit sentence loop
                                else:
                                    chunks.append(current_chunk.strip())
                                    current_chunk = sentence + ". "
                            else:
                                chunks.append(sentence)
                                current_chunk = ""
                        else:
                            current_chunk += sentence + ". "
                        j += 1
            else:
                current_chunk += paragraph + "\n\n"
            
            i += 1
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks

    def translate_chunk(self, chunk):
        """Dịch một chunk text"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.translation_prompt},
                    {"role": "user", "content": chunk}
                ],
                temperature=0.1,
                max_tokens=50000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Lỗi khi dịch chunk: {e}")
            return f"[LỖI DỊCH] {chunk}"

    def translate_file(self, input_file):
        """Dịch một file"""
        logger.info(f"Bắt đầu dịch file: {input_file}")
        
        # Đọc nội dung file
        content = self.read_file_content(input_file)
        
        # Chia thành chunks
        chunks = self.translate_text_chunks(content)
        logger.info(f"Chia thành {len(chunks)} chunks")
        
        # Dịch từng chunk
        translated_chunks = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Dịch chunk {i+1}/{len(chunks)}")
            translated_chunk = self.translate_chunk(chunk)
            translated_chunks.append(translated_chunk)
            
            # Tạm dừng để tránh rate limit
            time.sleep(1)
        
        # Ghép lại thành văn bản hoàn chỉnh
        translated_content = "\n\n".join(translated_chunks)
        
        # Lưu file dịch
        output_file = input_file.replace(".txt", "_vi.txt")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(translated_content)
        
        logger.info(f"Đã lưu bản dịch: {output_file}")
        return output_file

    def translate_all_files(self):
        """Dịch tất cả các file chưa có bản dịch"""
        untranslated_files = self.find_untranslated_files()
        
        if not untranslated_files:
            logger.info("Không có file nào cần dịch!")
            return
        
        logger.info(f"Tìm thấy {len(untranslated_files)} file cần dịch")
        
        for i, file_path in enumerate(untranslated_files):
            try:
                logger.info(f"Tiến độ: {i+1}/{len(untranslated_files)}")
                self.translate_file(file_path)
                logger.info(f"Hoàn thành dịch file: {file_path}")
                
                # Tạm dừng giữa các file
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Lỗi khi dịch file {file_path}: {e}")
                continue
        
        logger.info("Hoàn thành dịch tất cả các file!")

def main():
    """Hàm chính"""
    # Kiểm tra API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Vui lòng thiết lập OPENAI_API_KEY trong environment variables")
        return
    
    translator = PaperTranslator()
    
    print("🚀 Bắt đầu quá trình dịch các file paper...")
    translator.translate_all_files()
    print("✅ Hoàn thành!")

if __name__ == "__main__":
    main()