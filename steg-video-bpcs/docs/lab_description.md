# Lab: Giau tin trong video bang BPCS

## Muc tieu

Sinh vien thuc hanh giau tin trong video bang phuong phap mat phang bit BPCS o muc nang cao hon. Bai lab dua tren y tuong trong giao trinh: tach video thanh cac khung, chia mot kenh mau cua frame thanh block 8x8, tinh do phuc tap cua mat phang bit, chon vung nhieu de nhung thong diep, tao location map bang khoa chia se va danh gia chat luong video sau khi nhung.

## Mo hinh lab

Lab gom hai container:

- `server`: tao cover video, phan tich dung luong BPCS, tao payload co magic/length/CRC, nhung payload vao cac block BPCS va phuc vu file qua HTTP.
- `client`: tai video va metadata, tu tai tao location map bang khoa chia se, trich xuat payload, kiem CRC va so sanh thong diep.

## Nhiem vu

1. Tren `server`, tao video goc:

   ```bash
   ./create_cover_video.py
   ```

2. Phan tich dung luong giau tin cho nhieu bo tham so `bit_plane` va `alpha`:

   ```bash
   ./analyze_bpcs_capacity.py cover.mp4 capacity_report.json
   cat capacity_report.json
   ```

   Sinh vien can giai thich vi sao bit-plane cao hon thuong co dung luong nhieu hon, nhung co the lam video de bi nhan thay hon.

3. Tao payload:

   ```bash
   ./prepare_payload.py secret_message.txt payload_bits.txt payload_meta.json
   ```

4. Doc cac ham trong `embed_bpcs.py`:

   - `complexity(block_bits)`: tinh ty le chuyen tiep 0/1 theo chieu ngang va doc tren block 8x8.
   - `payload_pattern(bit, frame_index, block_index, block_size)`: tao mau bit-plane co do phuc tap cao. Khac voi cach dat ca block thanh 0/1, mau nay van giu block la vung nhieu de ben nhan co the tai tao location map.
   - `noisy_positions(...)`: lap location map tu nhung block co `complexity >= alpha`.

5. Nhung payload:

   ```bash
   ./embed_bpcs.py cover.mp4 payload_bits.txt stego_key.txt public/stego_bpcs.mp4 payload_meta.json
   ```

   Metadata cong khai khong chua `selected_positions`. Vi tri nhung duoc suy ra tu video, tham so BPCS va khoa `stego_key.txt`.

6. Tao bao cao chat luong:

   ```bash
   ./quality_report.py cover.mp4 public/stego_bpcs.mp4 metrics.json
   cat metrics.json
   ```

7. Phuc vu thu muc `public`:

   ```bash
   cd public
   python3 -m http.server 8000
   ```

8. Tren `client`, tai video va metadata:

   ```bash
   wget http://server:8000/stego_bpcs.mp4
   wget http://server:8000/payload_meta.json
   ```

9. Trich xuat thong diep. Script se tu quet lai block nhieu tren video stego, dung khoa de shuffle candidate list va lay dung so bit trong metadata:

   ```bash
   ./extract_bpcs.py stego_bpcs.mp4 payload_meta.json stego_key.txt extracted_message.txt
   ```

10. So sanh ket qua:

   ```bash
   ./compare_file.py expected_message.txt extracted_message.txt
   ```

## Cau hoi bao cao

1. Vi sao BPCS chon vung co do phuc tap cao de nhung tin?
2. Nguong `alpha = 0.3` co tac dong gi den dung luong giau tin?
3. Vi sao metadata khong nen cong khai truc tiep `selected_positions`?
4. Tai sao mau payload can giu do phuc tap cao thay vi gan ca block thanh 0 hoac 1?
5. Tai sao lab can magic, length va CRC?
6. Neu tang `bit_plane`, PSNR va kha nang bi phat hien thay doi the nao?
7. Neu ben nhan dung sai khoa, extractor se hong o buoc nao?
