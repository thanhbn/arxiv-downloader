# CLAUDE.md

Tệp này cung cấp hướng dẫn cho Claude Code (claude.ai/code) khi làm việc với mã trong kho lưu trữ này.

## Các Lệnh Thông Dụng

### Tải Xuống Bài Báo (Tối Ưu - Xử Lý Song Song)
```bash
# Tải xuống bài báo sử dụng script Python tối ưu (mặc định 8 worker)
python arxiv_downloader.py <url_file>

# Ví dụ:
python arxiv_downloader.py CoT.txt
python arxiv_downloader.py RAG.txt
python arxiv_downloader.py Benchmark.txt

# CẢNH BÁO: ArXiv chỉ cho phép 1 kết nối đồng thời và độ trễ 3 giây!
# Chỉ sử dụng 1 worker để tuân thủ giới hạn tốc độ ArXiv
python arxiv_downloader.py CoT.txt 1

# Tải xuống vào thư mục tùy chỉnh (ĐÃ SỬA)
python arxiv_downloader.py multimodal/arxiv_links.txt 1 multimodal

# Orchestrator (tuân thủ giới hạn tốc độ ArXiv) - ĐÃ SỬA để lưu vào thư mục đúng
python arxiv_orchestrator.py

# THẬN TRỌNG: Nhiều kết nối đồng thời có thể bị ArXiv chặn
python arxiv_orchestrator.py 1 1

# Tải xuống sử dụng shell script (tùy chọn dự phòng)
./download_arxiv.sh <links_file> <destination_directory>
```

### Kiểm Tra Tải Xuống
```bash
# Kiểm tra với bộ sưu tập nhỏ (nhanh với xử lý song song)
python arxiv_downloader.py icl.txt

# Kiểm tra với số lượng worker tùy chỉnh
python arxiv_downloader.py icl.txt 4

# Kiểm tra các tệp đã tải xuống
ls -la multimodal_papers/
ls -la CoT/
ls -la RAG/
```

### Chuyển Đổi PDF sang TXT
```bash
# Chuyển đổi tất cả PDF trong một bộ sưu tập sang định dạng TXT với đặt tên phù hợp
python3 pdf_to_txt_converter.py --all

# Chuyển đổi PDF trong bộ sưu tập cụ thể
python3 pdf_to_txt_converter.py --both --collection pruning

# Chỉ chuyển đổi PDF sang TXT (không đổi tên)
python3 pdf_to_txt_converter.py --convert --collection clarify

# Chỉ đổi tên các tệp TXT hiện có với tiêu đề bài báo (chức năng kiểm tra lại)
python3 pdf_to_txt_converter.py --rename --collection pruning

# Chế độ tương tác - chọn tùy chọn thủ công
python3 pdf_to_txt_converter.py

# Xử lý bộ sưu tập cụ thể với cả chuyển đổi và đổi tên
python3 pdf_to_txt_converter.py --collection multimodal

# Nhận trợ giúp với tất cả các tùy chọn có sẵn
python3 pdf_to_txt_converter.py --help
```

### Tổ Chức & Quản Lý Bài Báo
```bash
# Kiểm tra tổ chức bài báo so với các tệp arxiv_links.txt (chạy thử)
python3 check_and_move_papers_enhanced.py

# Thực sự di chuyển các bài báo đặt sai chỗ đến bộ sưu tập đúng
python3 check_and_move_papers_enhanced.py --execute

# Chỉ xử lý các bộ sưu tập cụ thể
python3 check_and_move_papers_enhanced.py --collections multimodal rag peft

# Ghi nhật ký nâng cao với các mức độ khác nhau
python3 check_and_move_papers_enhanced.py --log-level DEBUG --verbose

# Lưu nhật ký chi tiết vào tệp
python3 check_and_move_papers_enhanced.py --log-file organization.log --execute

# Chạy đầy đủ tính năng với ghi nhật ký toàn diện
python3 check_and_move_papers_enhanced.py --execute --verbose --log-level INFO --log-file full_organization.log
```

### Tham Khảo Lệnh & Trợ Giúp
```bash
# Hiển thị bảng ghi nhớ lệnh toàn diện với tất cả các script có sẵn
./cheatsheet.sh

# Liệt kê tất cả các script có sẵn mà không có mô tả
./cheatsheet.sh -l

# Nhận trợ giúp chi tiết cho script cụ thể
./cheatsheet.sh --help-for pdf_to_txt_converter.py
./cheatsheet.sh --help-for arxiv_downloader.py

# Hiển thị các tùy chọn sử dụng bảng ghi nhớ
./cheatsheet.sh --help

# Truy cập nhanh vào trợ giúp script bất kỳ (phương pháp thay thế)
./cheatsheet.sh pdf_to_txt_converter.py
```

## Tổng Quan Kiến Trúc

Đây là một công cụ tải xuống bài báo ArXiv được thiết kế cho việc thu thập bài báo nghiên cứu học thuật với các thành phần sau:

### Các Thành Phần Cốt Lõi

#### Python Downloader (arxiv_downloader.py) - TỐI ỬU
- **Xử Lý Song Song**: Tải xuống đồng thời lên đến 8 bài báo sử dụng ThreadPoolExecutor
- **Giới Hạn Tốc Độ Thông Minh**: Độ trễ ngẫu nhiên (0.3-0.8s) để tránh làm quá tải máy chủ
- **Xử Lý Lỗi Nâng Cao**: Logic thử lại mạnh mẽ và bảo vệ tệp tạm
- **Thống Kê Thời Gian Thực**: Theo dõi tiến trình với tóm tắt tải xuống
- **Worker Có Thể Cấu Hình**: Tính song song có thể điều chỉnh (1-16 worker)
- **Toàn Vẹn Tệp**: Sử dụng tệp tạm thời để ngăn chặn hỏng

#### Orchestrator (arxiv_orchestrator.py) - TỐI ỬU  
- **Xử Lý Bất Đồng Bộ**: Xử lý nhiều bộ sưu tập đồng thời
- **Theo Dõi Tiến Trình JSON**: Tiến trình bền vững với dấu thời gian và khôi phục
- **Chỉ Số Hiệu Suất**: Báo cáo chi tiết so sánh hiệu suất tuần tự vs song song
- **Tính Song Song Có Thể Cấu Hình**: Số lượng bộ sưu tập và worker có thể tùy chỉnh
- **Khôi Phục Lỗi**: Xử lý nhẹ nhàng timeout và lỗi

#### Shell Script (download_arxiv.sh) - Dự Phòng Cũ
- Script bash nâng cao với các tính năng tiên tiến
- Giới hạn tốc độ có thể cấu hình (mặc định: 3 giây giữa các lần tải xuống)
- Xử lý lỗi toàn diện với logic thử lại (lên đến 3 lần thử)
- Đầu ra có màu để có trải nghiệm người dùng tốt hơn
- Theo dõi tiến trình và tóm tắt tải xuống
- Header User-Agent phù hợp để nhận dạng là robot nghiên cứu

#### Công Cụ Tham Khảo Lệnh (cheatsheet.sh) - HỆ THỐNG TRỢ GIÚP TƯƠNG TÁC
- **Khám Phá Tự Động**: Tự động tìm và phân loại tất cả script Python và shell trong thư mục
- **Đầu Ra Có Màu**: Các phần và lệnh có mã màu để dễ đọc
- **Nhiều Định Dạng Trợ Giúp**: Hỗ trợ kiểm tra tùy chọn --help, -h, và help cho mỗi script
- **Hiển Thị Phân Loại**: Tổ chức script theo chức năng (Tải xuống, Xử lý PDF, Tổ chức, Phát triển, Thiết lập, Tiện ích)
- **Trích Xuất Mô Tả**: Tự động trích xuất mô tả từ docstring và chú thích tệp
- **Điều Hướng Tương Tác**: Truy cập nhanh vào trợ giúp và ví dụ sử dụng script cụ thể
- **Chế Độ Danh Sách**: Liệt kê gọn gàng tất cả script có sẵn mà không có mô tả
- **Phát Hiện Script**: Nhận dạng 22+ script và các tùy chọn trợ giúp được hỗ trợ
- **Ví Dụ Sử Dụng**: Bao gồm ví dụ khởi động nhanh và mẫu sử dụng phổ biến

#### PDF to TXT Converter (pdf_to_txt_converter.py) - NÂNG CAO
- **Hỗ Trợ Đa Thư Viện**: Sử dụng PyPDF2 (chính) và pdfplumber (dự phòng) để trích xuất văn bản mạnh mẽ
- **Đổi Tên Thông Minh**: Tự động đổi tên tệp từ ID arxiv để bao gồm tiêu đề bài báo
- **Xử Lý Từng Trang**: Trích xuất văn bản với điểm đánh dấu trang rõ ràng và xử lý lỗi
- **Trích Xuất Bảng**: Cố gắng trích xuất bảng khi trích xuất văn bản thông thường thất bại
- **Chức Năng Kiểm Tra Lại**: Có thể đổi tên các tệp TXT hiện có mà không cần chuyển đổi lại PDF
- **Hỗ Trợ Bộ Sưu Tập**: Xử lý các bộ sưu tập cụ thể hoặc tất cả bộ sưu tập tự động
- **Hoạt Động Kết Hợp**: Hỗ trợ đối số dòng lệnh hỗn hợp (--rename --collection)
- **Khôi Phục Lỗi**: Xử lý nhẹ nhàng lỗi trích xuất với báo cáo lỗi chi tiết
- **Chuẩn Hóa Tên Tệp**: Xử lý ký tự đặc biệt và giới hạn độ dài cho khả năng tương thích hệ thống tệp

#### Script Tổ Chức Bài Báo
**check_and_move_papers_enhanced.py** - Quản Lý Bộ Sưu Tập Nâng Cao
- **Ghi Nhật Ký Toàn Diện**: Dấu thời gian, mức nhật ký (DEBUG/INFO/WARNING/ERROR), đầu ra tệp
- **Phát Hiện Bài Báo Thông Minh**: Quét tất cả tệp arxiv_links.txt trên 156+ bộ sưu tập
- **Di Chuyển Thông Minh**: Tìm các bài báo đặt sai chỗ và di chuyển chúng đến thư mục bộ sưu tập đúng
- **Theo Dõi Tiến Trình**: Chỉ báo tiến trình thời gian thực với tỷ lệ hoàn thành phần trăm
- **Xử Lý Lỗi**: Khôi phục lỗi mạnh mẽ với báo cáo lỗi chi tiết
- **Chế Độ Chạy Thử**: Chế độ xem trước an toàn để xem những gì sẽ được di chuyển trước khi thực thi
- **Lọc Bộ Sưu Tập**: Xử lý các bộ sưu tập cụ thể hoặc tất cả bộ sưu tập
- **Chỉ Số Hiệu Suất**: Theo dõi thời gian thực thi và thống kê tóm tắt
- **Chỉ Báo Trạng Thái**: Trạng thái trực quan với emoji (✓✗?) để dễ đọc hơn

### Bộ Sưu Tập Bài Báo

Kho lưu trữ chứa các bộ sưu tập bài báo arXiv được tuyển chọn, tổ chức theo chủ đề nghiên cứu:

#### Bộ Sưu Tập Chính
- **CoT/** - Các bài báo về lý luận Chain of Thought
- **RAG/** - Các bài báo Retrieval-Augmented Generation  
- **Benchmark/** - Các bài báo về benchmarking và đánh giá
- **icl-papers/** - Các bài báo In-Context Learning
- **multimodal_papers/** - Các bài báo nghiên cứu AI đa phương thức

#### Bộ Sưu Tập Chuyên Biệt (156+ tổng cộng)
Hệ thống hiện hỗ trợ 156+ bộ sưu tập nghiên cứu chuyên biệt, mỗi bộ có tệp `arxiv_links.txt` riêng:
- **peft/** - Parameter-Efficient Fine-Tuning
- **multilingual/** - Mô hình ngôn ngữ đa ngôn ngữ
- **diffusion/** - Mô hình diffusion và sinh tạo
- **attention/** - Cơ chế attention
- **quantization/** - Kỹ thuật lượng tử hóa mô hình
- **interpretability/** - Khả năng diễn giải và giải thích mô hình
- **knowledge-graph/** - Tích hợp đồ thị tri thức
- **long-context/** - Xử lý ngữ cảnh dài
- **math/** - Lý luận toán học
- **medical/** - Ứng dụng AI y tế
- Và nhiều lĩnh vực chuyên biệt khác...

### Tệp URL

Các tệp văn bản chứa URL PDF arXiv để tải xuống hàng loạt:
- `CoT.txt` - URL bài báo Chain of Thought
- `RAG.txt` - URL bài báo RAG
- `Benchmark.txt` - URL bài báo Benchmark
- `icl.txt` - URL bài báo In-Context Learning
- `arxiv_links.txt` - URL bài báo Multimodal

## Mẫu Sử Dụng

### Quy Trình Tải Xuống Cơ Bản
1. Chọn một tệp URL (ví dụ: `CoT.txt`)
2. Chạy trình tải xuống: `python arxiv_downloader.py CoT.txt`
3. Các bài báo được tải xuống vào một thư mục được đặt tên theo tệp đầu vào (ví dụ: `CoT/`)

### Quy Trình Khám Phá Lệnh
1. **Tổng quan nhanh**: Chạy `./cheatsheet.sh` để xem tất cả lệnh có sẵn với mô tả
2. **Tìm trợ giúp cụ thể**: Sử dụng `./cheatsheet.sh --help-for TÊN_SCRIPT` để có trợ giúp script chi tiết
3. **Liệt kê tất cả script**: Sử dụng `./cheatsheet.sh -l` để liệt kê script gọn gàng
4. **Nhận ví dụ**: Kiểm tra phần ví dụ khởi động nhanh trong đầu ra bảng ghi nhớ

### Quy Trình Chuyển Đổi PDF sang TXT
1. **Tải xuống bài báo**: Sử dụng arxiv_downloader.py để lấy tệp PDF
2. **Chuyển đổi sang TXT**: Sử dụng pdf_to_txt_converter.py để trích xuất văn bản với đặt tên phù hợp
3. **Kiểm tra lại hiện có**: Sử dụng tùy chọn --rename để sửa tên tệp của các tệp đã chuyển đổi
4. **Xử lý hàng loạt**: Sử dụng --all để xử lý tất cả bộ sưu tập tự động

### Tải Xuống Nâng Cao với Shell Script
1. Sử dụng shell script để xử lý lỗi và theo dõi tiến trình tốt hơn
2. Ví dụ: `./download_arxiv.sh RAG.txt ./my_papers`
3. Cấu hình giới hạn tốc độ bằng cách sửa đổi các biến ở đầu script

### Hiệu Suất & Giới Hạn Tốc Độ
Các script tối ưu cung cấp cải thiện hiệu suất đáng kể trong khi tôn trọng giới hạn máy chủ:

#### Tuân Thủ Giới Hạn Tốc Độ ArXiv ⚠️
- **QUAN TRỌNG**: ArXiv chỉ cho phép **1 kết nối đồng thời** và **độ trễ 3+ giây**
- **Cài đặt mặc định**: 1 worker, độ trễ 3-3.5s để tuân thủ chính sách ArXiv
- **Rủi ro vi phạm**: Chặn IP, lỗi yêu cầu, từ chối dịch vụ
- **Chính sách chính thức**: "không thực hiện quá một yêu cầu mỗi ba giây"

#### Cân Nhắc Hiệu Suất
- **Tính năng nâng cao**: Xử lý lỗi tốt hơn, theo dõi tiến trình, bền vững JSON
- **Xử lý bất đồng bộ**: I/O không chặn cho quản lý bộ sưu tập  
- **Thử lại thông minh**: Tự động lùi lại khi có lỗi máy chủ
- **Toàn vẹn tệp**: Xử lý tệp tạm thời để ngăn chặn hỏng

#### Cấu Hình Giới Hạn Tốc Độ
- **Python downloader**: Độ trễ 3-3.5s giữa các lần tải xuống (tuân thủ ArXiv)
- **Orchestrator**: Xử lý bộ sưu tập tuần tự với độ trễ phù hợp
- **Shell script**: Độ trễ 3 giây (có thể cấu hình qua `SLEEP_BETWEEN_DOWNLOADS`)
- **Thích ứng**: Tự động lùi lại khi có lỗi máy chủ

#### Khuyến Nghị Sử Dụng An Toàn
- **Luôn sử dụng**: Chỉ 1 worker (mặc định)
- **Tôn trọng độ trễ**: 3+ giây giữa các yêu cầu
- **Giám sát**: Theo dõi lỗi 429/403 chỉ ra giới hạn tốc độ
- **Kiên nhẫn**: Tuân thủ ArXiv có nghĩa là tải xuống chậm hơn nhưng đáng tin cậy

## Tổ Chức Tệp

Các bài báo được tự động tổ chức theo chủ đề nghiên cứu thông qua cấu trúc thư mục được tạo bởi tên tệp đầu vào. Điều này cho phép phân loại và truy xuất dễ dàng các bài báo theo lĩnh vực chủ đề.

### Tổ Chức Bài Báo Tự Động
Hệ thống tổ chức nâng cao đảm bảo các bài báo được đặt trong thư mục bộ sưu tập đúng:

1. **Phát Hiện Bộ Sưu Tập**: Tự động quét tất cả thư mục con để tìm tệp `arxiv_links.txt`
2. **Khớp Bài Báo**: Trích xuất ID arXiv từ URL và tìm các tệp PDF tương ứng
3. **Di Chuyển Thông Minh**: Nhận dạng các bài báo đặt sai chỗ và di chuyển chúng đến bộ sưu tập đúng
4. **Kiểm Tra Toàn Vẹn**: Xác minh mỗi bộ sưu tập so với tệp `arxiv_links.txt` của nó
5. **Báo Cáo Toàn Diện**: Cung cấp thống kê chi tiết về độ hoàn chỉnh bộ sưu tập

### Quy Trình Tổ Chức
```bash
# Bước 1: Kiểm tra trạng thái tổ chức hiện tại
python3 check_and_move_papers_enhanced.py --verbose

# Bước 2: Xem lại những gì sẽ được di chuyển (chạy thử)
python3 check_and_move_papers_enhanced.py --collections multimodal rag

# Bước 3: Thực thi tổ chức với ghi nhật ký
python3 check_and_move_papers_enhanced.py --execute --log-file organization.log

# Bước 4: Xác minh tổ chức hoàn thành thành công
python3 check_and_move_papers_enhanced.py --log-level WARNING
```

### Theo Dõi Độ Hoàn Chỉnh Bộ Sưu Tập
- **Tỷ Lệ Hoàn Thành**: Tỷ lệ phần trăm các bài báo mong đợi có mặt trong mỗi bộ sưu tập
- **Bài Báo Thiếu**: Các bài báo được liệt kê trong `arxiv_links.txt` nhưng không tìm thấy trong thư mục bộ sưu tập
- **Bài Báo Thừa**: Các bài báo trong thư mục bộ sưu tập nhưng không được liệt kê trong `arxiv_links.txt`
- **Tìm Kiếm Toàn Cục**: Tự động phát hiện các bài báo đặt sai chỗ trên tất cả bộ sưu tập