Khái niệm	Hiểu đơn giản	Liên quan gì tới dự án
Token	Mẩu chữ mà model đọc và viết. Một từ có thể là 1 hoặc nhiều token	Tiếng Việt có dấu thường tốn nhiều token hơn tiếng Anh cùng nghĩa, nên tốn tiền hơn
Context window	Số token tối đa model “nhìn thấy” trong một lần gọi (câu hỏi + tài liệu + câu trả lời)	Giai đoạn 2 nhét tài liệu vào prompt, nên không được vượt giới hạn này
Temperature	Độ “ngẫu hứng”. 0 thì gần như lần nào trả lời cũng giống nhau	Khi eval nên để 0 để điểm ổn định
Giá theo token	Tiền = token vào × giá vào + token ra × giá ra (giá thường tính theo 1 triệu token). Token ra thường đắt hơn	Chi phí eval = số câu × chi phí mỗi câu, nên bộ eval cho PR phải nhỏ
