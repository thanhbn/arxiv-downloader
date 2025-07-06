"""
Keyword Extraction Tool for Academic Papers
Hỗ trợ nhiều thuật toán để trích xuất từ khóa quan trọng từ paper
"""

import re
import numpy as np
from collections import Counter
from typing import List, Tuple, Dict
import PyPDF2
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
import yake

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    print("Downloading NLTK data...")
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)


class KeywordExtractor:
    """Lớp chính để trích xuất từ khóa từ văn bản"""
    
    def __init__(self, language='english'):
        self.language = language
        self.stop_words = set(stopwords.words(language))
        
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Trích xuất văn bản từ file PDF"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"Lỗi khi đọc PDF: {e}")
            return ""
    
    def clean_text(self, text: str) -> str:
        """Làm sạch văn bản"""
        # Loại bỏ ký tự đặc biệt và số
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\d+', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def extract_keywords_frequency(self, text: str, top_n: int = 20) -> List[Tuple[str, int]]:
        """Trích xuất từ khóa dựa trên tần suất xuất hiện"""
        # Làm sạch văn bản
        cleaned_text = self.clean_text(text)
        
        # Tokenize
        words = word_tokenize(cleaned_text.lower())
        
        # Lọc từ có ít nhất 3 ký tự và không phải stop words
        words = [word for word in words if len(word) >= 3 and word not in self.stop_words]
        
        # Đếm tần suất
        word_freq = Counter(words)
        return word_freq.most_common(top_n)
    
    def extract_keywords_tfidf(self, text: str, max_features: int = 20) -> List[Tuple[str, float]]:
        """Trích xuất từ khóa sử dụng TF-IDF"""
        try:
            # Chia văn bản thành các câu để tạo corpus
            sentences = sent_tokenize(text)
            if len(sentences) < 2:
                sentences = [text]
            
            vectorizer = TfidfVectorizer(
                max_features=max_features,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.8
            )
            
            tfidf_matrix = vectorizer.fit_transform(sentences)
            feature_names = vectorizer.get_feature_names_out()
            
            # Tính điểm trung bình cho mỗi từ
            mean_scores = np.mean(tfidf_matrix.toarray(), axis=0)
            
            # Sắp xếp theo điểm số
            keyword_scores = list(zip(feature_names, mean_scores))
            keyword_scores.sort(key=lambda x: x[1], reverse=True)
            
            return keyword_scores
        except Exception as e:
            print(f"Lỗi TF-IDF: {e}")
            return []
    
    def extract_keywords_yake(self, text: str, max_ngram: int = 3, num_keywords: int = 20) -> List[Tuple[str, float]]:
        """Trích xuất từ khóa sử dụng YAKE"""
        try:
            kw_extractor = yake.KeywordExtractor(
                lan="en",
                n=max_ngram,
                dedupLim=0.9,
                top=num_keywords,
                features=None
            )
            keywords = kw_extractor.extract_keywords(text)
            return keywords
        except Exception as e:
            print(f"Lỗi YAKE: {e}")
            return []
    
    def extract_keywords_combined(self, text: str, top_n: int = 15) -> Dict[str, List]:
        """Kết hợp nhiều phương pháp để có kết quả tốt hơn"""
        results = {}
        
        # Frequency-based
        freq_keywords = self.extract_keywords_frequency(text, top_n)
        results['frequency'] = freq_keywords
        
        # TF-IDF
        tfidf_keywords = self.extract_keywords_tfidf(text, top_n)
        results['tfidf'] = tfidf_keywords
        
        # YAKE
        yake_keywords = self.extract_keywords_yake(text, num_keywords=top_n)
        results['yake'] = yake_keywords
        
        return results
    
    def process_paper(self, file_path: str, method: str = 'combined', top_n: int = 15) -> Dict:
        """Xử lý một paper và trích xuất từ khóa"""
        print(f"Đang xử lý: {file_path}")
        
        # Trích xuất văn bản
        if file_path.endswith('.pdf'):
            text = self.extract_text_from_pdf(file_path)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        
        if not text:
            return {"error": "Không thể trích xuất văn bản"}
        
        # Trích xuất từ khóa
        if method == 'frequency':
            keywords = self.extract_keywords_frequency(text, top_n)
        elif method == 'tfidf':
            keywords = self.extract_keywords_tfidf(text, top_n)
        elif method == 'yake':
            keywords = self.extract_keywords_yake(text, num_keywords=top_n)
        else:  # combined
            keywords = self.extract_keywords_combined(text, top_n)
        
        return {
            "file": file_path,
            "text_length": len(text),
            "keywords": keywords,
            "method": method
        }


def main():
    """Hàm chính để test"""
    extractor = KeywordExtractor()
    
    # Test với văn bản mẫu
    sample_text = """
    Machine learning is a subset of artificial intelligence that focuses on algorithms 
    that can learn from data. Deep learning, a subset of machine learning, uses neural 
    networks with multiple layers. Natural language processing is another important 
    area of artificial intelligence that deals with text and speech.
    """
    
    print("=== Test Keyword Extraction ===")
    print("\n1. Frequency-based:")
    freq_results = extractor.extract_keywords_frequency(sample_text, 10)
    for word, count in freq_results:
        print(f"  {word}: {count}")
    
    print("\n2. TF-IDF:")
    tfidf_results = extractor.extract_keywords_tfidf(sample_text, 10)
    for word, score in tfidf_results:
        print(f"  {word}: {score:.3f}")
    
    print("\n3. YAKE:")
    yake_results = extractor.extract_keywords_yake(sample_text, num_keywords=10)
    for word, score in yake_results:
        print(f"  {word}: {score:.3f}")


if __name__ == "__main__":
    main()