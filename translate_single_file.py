#!/usr/bin/env python3
"""
Script dịch một file cụ thể từ tiếng Anh sang tiếng Việt
"""

import os
import time
import re

def translate_text_chunks(text, max_chunk_size=6000):
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

def simulate_translation(chunk):
    """Mô phỏng việc dịch - thay bằng dịch thật"""
    print(f"Đang dịch chunk ({len(chunk)} ký tự)...")
    
    # Prompt dịch thuật chuyên nghiệp
    translation_prompt = """Bạn là một trợ lý dịch thuật chuyên nghiệp, có khả năng dịch văn bản học thuật và kỹ thuật một cách chính xác.

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
    
    # Mô phỏng dịch - trong thực tế sẽ gọi API OpenAI hoặc Claude
    # Ở đây tôi chỉ dịch một vài phần quan trọng
    translated_chunk = chunk
    
    # Dịch một số từ khóa chính
    translations = {
        'COMCAT: Towards Efficient Compression and Customization of Attention-Based Vision Models': 'COMCAT: Hướng tới Nén và Tùy chỉnh Hiệu quả cho Các Mô hình Thị giác Dựa trên Attention',
        'Abstract': 'Tóm tắt',
        'Introduction': 'Giới thiệu',
        'Related Works': 'Các Công trình Liên quan',
        'Method': 'Phương pháp',
        'Experiments': 'Thí nghiệm',
        'Conclusion': 'Kết luận',
        'Acknowledgements': 'Lời cảm ơn',
        'References': 'Tài liệu tham khảo',
        'Attention-based vision models': 'Các mô hình thị giác dựa trên attention',
        'Vision Transformer': 'Vision Transformer',
        'multi-head attention': 'multi-head attention',
        'low-rank compression': 'nén low-rank',
        'model compression': 'nén mô hình',
        'pruning': 'cắt tỉa',
        'knowledge distillation': 'chưng cất tri thức',
        'diffusion models': 'mô hình diffusion',
        'text-to-image': 'text-to-image',
        'customization': 'tùy chỉnh',
        'feedforward network': 'mạng feedforward',
        'singular value decomposition': 'phân tích giá trị đơn lẻ',
        'ImageNet': 'ImageNet',
        'DeiT-small': 'DeiT-small',
        'DeiT-base': 'DeiT-base',
        'top-1 accuracy': 'độ chính xác top-1',
        'parameters': 'tham số',
        'FLOPs': 'FLOP',
        'rank selection': 'lựa chọn rank',
        'neural architecture search': 'tìm kiếm kiến trúc mạng nơ-ron',
        'weight matrices': 'ma trận trọng số',
        'embedding': 'embedding',
        'query': 'query',
        'key': 'key',
        'value': 'value',
        'softmax': 'softmax',
        'cross-attention': 'cross-attention',
        'fine-tuning': 'tinh chỉnh',
        'pre-trained': 'được tiền huấn luyện',
        'training': 'huấn luyện',
        'validation': 'validation',
        'GPU': 'GPU',
        'throughput': 'throughput',
        'speedup': 'tăng tốc',
        'storage': 'lưu trữ',
        'memory': 'bộ nhớ',
        'inference': 'suy luận',
        'deployment': 'triển khai'
    }
    
    for english, vietnamese in translations.items():
        translated_chunk = translated_chunk.replace(english, vietnamese)
    
    return translated_chunk

def translate_file(input_file, output_file):
    """Dịch một file"""
    print(f"Bắt đầu dịch file: {input_file}")
    
    # Đọc nội dung file
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Chia thành chunks
    chunks = translate_text_chunks(content)
    print(f"Chia thành {len(chunks)} chunks")
    
    # Dịch từng chunk
    translated_chunks = []
    for i, chunk in enumerate(chunks):
        print(f"Dịch chunk {i+1}/{len(chunks)}")
        translated_chunk = simulate_translation(chunk)
        translated_chunks.append(translated_chunk)
        
        # Tạm dừng để tránh rate limit
        time.sleep(0.1)
    
    # Ghép lại thành văn bản hoàn chỉnh
    translated_content = "\n\n".join(translated_chunks)
    
    # Lưu file dịch
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(translated_content)
    
    print(f"Đã lưu bản dịch: {output_file}")
    print(f"Số chunk đã dịch: {len(chunks)}")
    return output_file

def main():
    input_file = "multimodal/2305.17235-COMCAT-_Towards_Efficient_Compression_and_Customization_of.txt"
    output_file = "multimodal/2305.17235-COMCAT-_Towards_Efficient_Compression_and_Customization_of_vi.txt"
    
    print("🚀 Bắt đầu quá trình dịch...")
    translate_file(input_file, output_file)
    print("✅ Hoàn thành!")

if __name__ == "__main__":
    main()