"""
Ví dụ sử dụng KeywordExtractor để trích xuất từ khóa từ paper
"""

import os
from keyword_extractor import KeywordExtractor

def example_usage():
    """Ví dụ sử dụng cơ bản"""
    extractor = KeywordExtractor()
    
    # Ví dụ 1: Xử lý văn bản trực tiếp
    print("=== Ví dụ 1: Xử lý văn bản trực tiếp ===")
    sample_text = """
    Transformer architecture has revolutionized natural language processing.
    The attention mechanism allows the model to focus on relevant parts of the input.
    BERT and GPT are popular transformer-based models for various NLP tasks.
    Fine-tuning pre-trained models has become a standard practice in machine learning.
    """
    
    # Sử dụng phương pháp kết hợp
    results = extractor.extract_keywords_combined(sample_text, top_n=10)
    
    print("Kết quả từ các phương pháp khác nhau:")
    for method, keywords in results.items():
        print(f"\n{method.upper()}:")
        for i, (word, score) in enumerate(keywords[:5], 1):
            print(f"  {i}. {word}: {score}")
    
    # Ví dụ 2: Xử lý file PDF (nếu có)
    print("\n=== Ví dụ 2: Xử lý file PDF ===")
    
    # Tìm file PDF đầu tiên trong thư mục
    pdf_files = []
    for root, dirs, files in os.walk("../"):
        for file in files:
            if file.endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
                break
        if pdf_files:
            break
    
    if pdf_files:
        pdf_path = pdf_files[0]
        print(f"Đang xử lý PDF: {pdf_path}")
        
        # Trích xuất từ khóa bằng TF-IDF
        result = extractor.process_paper(pdf_path, method='tfidf', top_n=10)
        
        if 'error' not in result:
            print(f"Độ dài văn bản: {result['text_length']} ký tự")
            print("Top 10 từ khóa:")
            for i, (word, score) in enumerate(result['keywords'][:10], 1):
                print(f"  {i}. {word}: {score:.3f}")
        else:
            print(f"Lỗi: {result['error']}")
    else:
        print("Không tìm thấy file PDF để test")
    
    # Ví dụ 3: So sánh các phương pháp
    print("\n=== Ví dụ 3: So sánh các phương pháp ===")
    
    tech_text = """
    Deep learning neural networks have shown remarkable performance in computer vision tasks.
    Convolutional neural networks are particularly effective for image classification.
    Recurrent neural networks excel at sequential data processing.
    Attention mechanisms have improved the performance of transformer models.
    Transfer learning allows models to leverage pre-trained knowledge.
    """
    
    methods = ['frequency', 'tfidf', 'yake']
    
    for method in methods:
        print(f"\n{method.upper()} - Top 5 từ khóa:")
        if method == 'frequency':
            keywords = extractor.extract_keywords_frequency(tech_text, 5)
        elif method == 'tfidf':
            keywords = extractor.extract_keywords_tfidf(tech_text, 5)
        else:  # yake
            keywords = extractor.extract_keywords_yake(tech_text, num_keywords=5)
        
        for i, (word, score) in enumerate(keywords[:5], 1):
            print(f"  {i}. {word}: {score}")


def batch_process_papers():
    """Xử lý hàng loạt paper trong thư mục"""
    extractor = KeywordExtractor()
    
    # Tìm tất cả file PDF
    pdf_files = []
    for root, dirs, files in os.walk("../"):
        for file in files:
            if file.endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    
    if not pdf_files:
        print("Không tìm thấy file PDF nào")
        return
    
    print(f"Tìm thấy {len(pdf_files)} file PDF")
    
    # Xử lý 3 file đầu tiên (để demo)
    for i, pdf_path in enumerate(pdf_files[:3], 1):
        print(f"\n=== Xử lý file {i}: {os.path.basename(pdf_path)} ===")
        
        result = extractor.process_paper(pdf_path, method='combined', top_n=8)
        
        if 'error' not in result:
            print(f"Kích thước văn bản: {result['text_length']} ký tự")
            
            # Hiển thị kết quả TF-IDF
            if 'tfidf' in result['keywords']:
                print("Top từ khóa (TF-IDF):")
                for j, (word, score) in enumerate(result['keywords']['tfidf'][:5], 1):
                    print(f"  {j}. {word}: {score:.3f}")
        else:
            print(f"Lỗi: {result['error']}")


if __name__ == "__main__":
    print("Chạy ví dụ sử dụng KeywordExtractor...")
    example_usage()
    
    print("\n" + "="*50)
    print("Xử lý hàng loạt paper...")
    batch_process_papers()