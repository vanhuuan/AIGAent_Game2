# Game Client Specification

1. **Game loop**  
   - Client tự quản lý vòng lặp (game loop) của mình, không sử dụng chung với server.

2. **Khi server khởi động**  
   - Server chờ kết nối từ:  
     + Dispatcher (kết nối đầu tiên, chịu trách nhiệm gửi message sự kiện xuống client)  
     + Các game client

3. **Sau khi các client kết nối**  
   - Client gọi hàm `get_player() → Player` để nhận trạng thái hiện tại của mình:  
     - `player.message`: message mà server gửi xuống client  
     - Client theo dõi xem có message mới hay không để xử lý  
     - Message đầu tiên sẽ chứa điều kiện hoàn thành game, ví dụ:  
       > “To complete this game, you need to collect 2 units of wood and 2 units of fabric. Every 3 units of cotton can be converted into 1 unit of fabric.”

4. **Client chỉ gửi request lên server qua các hàm sau**  
   - Gửi với **interval 1s**; server chỉ xử lý tối đa 1 request mỗi giây, ngoại trừ `get_player()` được trả về ngay lập tức.  
     1. `set_player_name(name)`: đặt tên player trước khi game start  
     2. `get_player()`: trả về thông tin player hiện tại  
     3. **Move**:  
        - `move(direction)`: di chuyển theo hướng (`0`=trái, `1`=phải, `2`=lên, `3`=xuống)  
        - Hoặc gọi trực tiếp `move_left()`, `move_right()`, `move_up()`, `move_down()`  
     4. `clear_in_process_messages()`: dọn bớt lệnh move nếu client gửi quá nhiều lên server  
     5. `allow_collect_items(items=[])`: cho phép client thu thập các loại resource, ví dụ:  
        ```python
        client.allow_collect_items(items=['w'])  # chỉ cho collect gỗ
        ```  
        Trong đó `items` có thể là:  
        - `'w'`: wood  
        - `'c'`: cotton  
     6. **Quy đổi fabric**  
        - Trên server, khi số cotton trong `player.store` là bội số của tỉ lệ hoán đổi (ví dụ 3 cotton → 1 fabric), thì tự động chuyển:  
          ```python
          # Ví dụ:
          player.store = ['w', 'w', 'w', 'c', 'c']
          # Khi client collect thêm 1 cotton:
          player.store → ['w', 'w', 'w', 'fa']
          ```  
        - Nhớ điều này để tính toán số cotton cần thu thập.
