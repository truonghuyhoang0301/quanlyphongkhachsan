import streamlit as st
import sqlite3
from datetime import datetime, date
from pathlib import Path
import pandas as pd

# ============================================================
# CẤU HÌNH
# ============================================================

st.set_page_config(
    page_title="Hotel Manager",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_FILE = Path("hotel.db")


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT UNIQUE NOT NULL,
            room_type TEXT NOT NULL,
            floor INTEGER NOT NULL,
            price REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Trống',
            note TEXT DEFAULT ''
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            id_card TEXT,
            address TEXT,
            note TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_id INTEGER NOT NULL,
            room_id INTEGER NOT NULL,
            check_in TEXT NOT NULL,
            check_out TEXT NOT NULL,
            adults INTEGER DEFAULT 1,
            children INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Đã đặt',
            total_price REAL DEFAULT 0,
            note TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (guest_id) REFERENCES guests(id),
            FOREIGN KEY (room_id) REFERENCES rooms(id)
        )
    """)

    # Dữ liệu phòng mẫu
    cursor.execute("SELECT COUNT(*) FROM rooms")
    room_count = cursor.fetchone()[0]

    if room_count == 0:
        sample_rooms = [
            ("101", "Standard", 1, 500000, "Trống", ""),
            ("102", "Standard", 1, 500000, "Trống", ""),
            ("103", "Standard", 1, 550000, "Trống", ""),
            ("201", "Deluxe", 2, 800000, "Trống", ""),
            ("202", "Deluxe", 2, 800000, "Trống", ""),
            ("203", "Deluxe", 2, 850000, "Trống", ""),
            ("301", "Suite", 3, 1200000, "Trống", ""),
            ("302", "Suite", 3, 1500000, "Trống", ""),
            ("401", "VIP", 4, 2000000, "Trống", ""),
            ("402", "VIP", 4, 2500000, "Trống", ""),
        ]

        cursor.executemany("""
            INSERT INTO rooms
            (room_number, room_type, floor, price, status, note)
            VALUES (?, ?, ?, ?, ?, ?)
        """, sample_rooms)

    conn.commit()
    conn.close()


init_database()


# ============================================================
# HÀM DATABASE
# ============================================================

def query_db(query, params=(), fetch=False):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(query, params)

    if fetch:
        result = cursor.fetchall()
        conn.close()
        return result

    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id


def get_rooms():
    return query_db(
        "SELECT * FROM rooms ORDER BY CAST(room_number AS INTEGER)",
        fetch=True
    )


def get_guests():
    return query_db(
        "SELECT * FROM guests ORDER BY id DESC",
        fetch=True
    )


def get_bookings():
    return query_db("""
        SELECT
            bookings.id,
            guests.full_name,
            guests.phone,
            rooms.room_number,
            rooms.room_type,
            bookings.check_in,
            bookings.check_out,
            bookings.adults,
            bookings.children,
            bookings.status,
            bookings.total_price,
            bookings.note,
            bookings.created_at
        FROM bookings
        JOIN guests ON bookings.guest_id = guests.id
        JOIN rooms ON bookings.room_id = rooms.id
        ORDER BY bookings.id DESC
    """, fetch=True)


# ============================================================
# FORMAT
# ============================================================

def format_money(value):
    return f"{value:,.0f} ₫".replace(",", ".")


def status_color(status):
    colors = {
        "Trống": "🟢",
        "Đang ở": "🔵",
        "Đã đặt": "🟡",
        "Bảo trì": "🔴",
        "Đã trả": "⚪",
        "Hủy": "⚫",
    }
    return colors.get(status, "⚪")


def calculate_nights(check_in, check_out):
    days = (check_out - check_in).days
    return max(days, 1)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.title("🏨 Hotel Manager")
    st.caption("Hệ thống quản lý khách sạn")

    st.divider()

    page = st.radio(
        "MENU",
        [
            "📊 Tổng quan",
            "🛏️ Quản lý phòng",
            "👤 Khách hàng",
            "📅 Đặt phòng",
            "💰 Doanh thu",
        ]
    )

    st.divider()

    st.caption("Hotel Management System")
    st.caption("SQLite + Streamlit")


# ============================================================
# DASHBOARD
# ============================================================

if page == "📊 Tổng quan":

    st.title("📊 Tổng quan khách sạn")
    st.caption(f"Cập nhật: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    rooms = get_rooms()
    guests = get_guests()
    bookings = get_bookings()

    room_df = pd.DataFrame([dict(r) for r in rooms])
    booking_df = pd.DataFrame([dict(b) for b in bookings])

    total_rooms = len(rooms)
    empty_rooms = len([
        r for r in rooms
        if r["status"] == "Trống"
    ])
    occupied_rooms = len([
        r for r in rooms
        if r["status"] == "Đang ở"
    ])
    reserved_rooms = len([
        r for r in rooms
        if r["status"] == "Đã đặt"
    ])
    maintenance_rooms = len([
        r for r in rooms
        if r["status"] == "Bảo trì"
    ])

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Tổng phòng", total_rooms)
    col2.metric("Phòng trống", empty_rooms)
    col3.metric("Đang ở", occupied_rooms)
    col4.metric("Đã đặt", reserved_rooms)
    col5.metric("Bảo trì", maintenance_rooms)

    st.divider()

    # Tỷ lệ sử dụng
    if total_rooms > 0:
        occupied_percent = (
            (occupied_rooms + reserved_rooms) / total_rooms
        ) * 100
    else:
        occupied_percent = 0

    st.subheader("📈 Tình trạng phòng")

    st.progress(
        int(min(occupied_percent, 100)),
        text=f"Công suất sử dụng: {occupied_percent:.1f}%"
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🛏️ Phòng hiện tại")

        status_data = pd.DataFrame({
            "Trạng thái": [
                "Trống",
                "Đang ở",
                "Đã đặt",
                "Bảo trì"
            ],
            "Số phòng": [
                empty_rooms,
                occupied_rooms,
                reserved_rooms,
                maintenance_rooms
            ]
        })

        st.bar_chart(
            status_data.set_index("Trạng thái")
        )

    with col2:
        st.subheader("📋 Booking gần đây")

        if len(bookings) > 0:
            recent = booking_df.head(5)

            display_df = recent[
                [
                    "full_name",
                    "room_number",
                    "check_in",
                    "check_out",
                    "status"
                ]
            ].copy()

            display_df.columns = [
                "Khách",
                "Phòng",
                "Check-in",
                "Check-out",
                "Trạng thái"
            ]

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Chưa có booking.")

    st.divider()

    # Doanh thu
    total_revenue = 0

    if len(bookings) > 0:
        for booking in bookings:
            if booking["status"] not in ["Hủy"]:
                total_revenue += booking["total_price"]

    st.metric(
        "💰 Tổng doanh thu booking",
        format_money(total_revenue)
    )


# ============================================================
# QUẢN LÝ PHÒNG
# ============================================================

elif page == "🛏️ Quản lý phòng":

    st.title("🛏️ Quản lý phòng")

    tabs = st.tabs([
        "📋 Danh sách phòng",
        "➕ Thêm phòng",
        "✏️ Chỉnh sửa phòng"
    ])

    # --------------------------------------------------------
    # DANH SÁCH
    # --------------------------------------------------------

    with tabs[0]:

        rooms = get_rooms()

        if rooms:

            # Bộ lọc
            col1, col2, col3 = st.columns(3)

            with col1:
                status_filter = st.selectbox(
                    "Trạng thái",
                    [
                        "Tất cả",
                        "Trống",
                        "Đang ở",
                        "Đã đặt",
                        "Bảo trì"
                    ]
                )

            with col2:
                type_filter = st.selectbox(
                    "Loại phòng",
                    ["Tất cả"] +
                    sorted(list(set(r["room_type"] for r in rooms)))
                )

            with col3:
                search_room = st.text_input(
                    "🔎 Tìm phòng",
                    placeholder="Ví dụ: 101"
                )

            filtered_rooms = []

            for room in rooms:

                if (
                    status_filter != "Tất cả"
                    and room["status"] != status_filter
                ):
                    continue

                if (
                    type_filter != "Tất cả"
                    and room["room_type"] != type_filter
                ):
                    continue

                if (
                    search_room
                    and search_room.lower()
                    not in room["room_number"].lower()
                ):
                    continue

                filtered_rooms.append(room)

            st.write(
                f"Hiển thị **{len(filtered_rooms)}** phòng"
            )

            for room in filtered_rooms:

                icon = status_color(room["status"])

                with st.container(border=True):

                    col1, col2, col3, col4, col5 = st.columns(
                        [1, 2, 2, 2, 1]
                    )

                    col1.markdown(
                        f"### 🛏️ {room['room_number']}"
                    )

                    col2.write(
                        f"**Loại:** {room['room_type']}"
                    )

                    col3.write(
                        f"**Giá:** {format_money(room['price'])}/đêm"
                    )

                    col4.write(
                        f"{icon} **{room['status']}**"
                    )

                    if col5.button(
                        "Xóa",
                        key=f"delete_room_{room['id']}"
                    ):

                        # Kiểm tra booking
                        booking_check = query_db(
                            """
                            SELECT COUNT(*)
                            FROM bookings
                            WHERE room_id = ?
                            """,
                            (room["id"],),
                            fetch=True
                        )[0][0]

                        if booking_check > 0:
                            st.error(
                                "Không thể xóa phòng đã có booking."
                            )
                        else:
                            query_db(
                                "DELETE FROM rooms WHERE id = ?",
                                (room["id"],)
                            )
                            st.success("Đã xóa phòng.")
                            st.rerun()

                    if room["note"]:
                        st.caption(
                            f"📝 {room['note']}"
                        )

        else:
            st.info("Chưa có phòng.")


    # --------------------------------------------------------
    # THÊM PHÒNG
    # --------------------------------------------------------

    with tabs[1]:

        st.subheader("➕ Thêm phòng mới")

        with st.form("add_room_form"):

            col1, col2 = st.columns(2)

            with col1:
                room_number = st.text_input(
                    "Số phòng *",
                    placeholder="Ví dụ: 501"
                )

                room_type = st.selectbox(
                    "Loại phòng",
                    [
                        "Standard",
                        "Superior",
                        "Deluxe",
                        "Suite",
                        "VIP"
                    ]
                )

            with col2:

                floor = st.number_input(
                    "Tầng",
                    min_value=1,
                    max_value=100,
                    value=1
                )

                price = st.number_input(
                    "Giá phòng / đêm",
                    min_value=0,
                    value=500000,
                    step=50000
                )

            note = st.text_area(
                "Ghi chú"
            )

            submitted = st.form_submit_button(
                "➕ Thêm phòng",
                type="primary"
            )

            if submitted:

                if not room_number.strip():
                    st.error("Vui lòng nhập số phòng.")

                else:
                    try:
                        query_db(
                            """
                            INSERT INTO rooms
                            (
                                room_number,
                                room_type,
                                floor,
                                price,
                                status,
                                note
                            )
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                room_number.strip(),
                                room_type,
                                floor,
                                price,
                                "Trống",
                                note
                            )
                        )

                        st.success(
                            f"Đã thêm phòng {room_number}."
                        )

                    except sqlite3.IntegrityError:
                        st.error(
                            "Số phòng này đã tồn tại."
                        )


    # --------------------------------------------------------
    # CHỈNH SỬA PHÒNG
    # --------------------------------------------------------

    with tabs[2]:

        rooms = get_rooms()

        if rooms:

            room_options = {
                f"{r['room_number']} - {r['room_type']}": r["id"]
                for r in rooms
            }

            selected_room_name = st.selectbox(
                "Chọn phòng",
                list(room_options.keys())
            )

            selected_id = room_options[selected_room_name]

            selected_room = next(
                r for r in rooms
                if r["id"] == selected_id
            )

            with st.form("edit_room_form"):

                col1, col2 = st.columns(2)

                with col1:

                    edit_number = st.text_input(
                        "Số phòng",
                        value=selected_room["room_number"]
                    )

                    edit_type = st.selectbox(
                        "Loại phòng",
                        [
                            "Standard",
                            "Superior",
                            "Deluxe",
                            "Suite",
                            "VIP"
                        ],
                        index=[
                            "Standard",
                            "Superior",
                            "Deluxe",
                            "Suite",
                            "VIP"
                        ].index(selected_room["room_type"])
                        if selected_room["room_type"]
                        in [
                            "Standard",
                            "Superior",
                            "Deluxe",
                            "Suite",
                            "VIP"
                        ]
                        else 0
                    )

                with col2:

                    edit_floor = st.number_input(
                        "Tầng",
                        min_value=1,
                        value=selected_room["floor"]
                    )

                    edit_price = st.number_input(
                        "Giá phòng",
                        min_value=0,
                        value=int(selected_room["price"]),
                        step=50000
                    )

                edit_status = st.selectbox(
                    "Trạng thái",
                    [
                        "Trống",
                        "Đang ở",
                        "Đã đặt",
                        "Bảo trì"
                    ],
                    index=[
                        "Trống",
                        "Đang ở",
                        "Đã đặt",
                        "Bảo trì"
                    ].index(selected_room["status"])
                    if selected_room["status"]
                    in [
                        "Trống",
                        "Đang ở",
                        "Đã đặt",
                        "Bảo trì"
                    ]
                    else 0
                )

                edit_note = st.text_area(
                    "Ghi chú",
                    value=selected_room["note"] or ""
                )

                save = st.form_submit_button(
                    "💾 Lưu thay đổi",
                    type="primary"
                )

                if save:

                    try:
                        query_db(
                            """
                            UPDATE rooms
                            SET
                                room_number = ?,
                                room_type = ?,
                                floor = ?,
                                price = ?,
                                status = ?,
                                note = ?
                            WHERE id = ?
                            """,
                            (
                                edit_number,
                                edit_type,
                                edit_floor,
                                edit_price,
                                edit_status,
                                edit_note,
                                selected_id
                            )
                        )

                        st.success("Đã cập nhật phòng.")
                        st.rerun()

                    except sqlite3.IntegrityError:
                        st.error(
                            "Số phòng đã tồn tại."
                        )


# ============================================================
# KHÁCH HÀNG
# ============================================================

elif page == "👤 Khách hàng":

    st.title("👤 Quản lý khách hàng")

    tabs = st.tabs([
        "📋 Danh sách",
        "➕ Thêm khách hàng"
    ])

    # --------------------------------------------------------
    # DANH SÁCH KHÁCH
    # --------------------------------------------------------

    with tabs[0]:

        guests = get_guests()

        search = st.text_input(
            "🔎 Tìm khách hàng",
            placeholder="Tên, số điện thoại hoặc CCCD"
        )

        filtered = []

        for guest in guests:

            text = " ".join([
                guest["full_name"] or "",
                guest["phone"] or "",
                guest["id_card"] or ""
            ]).lower()

            if search.lower() in text:
                filtered.append(guest)

        if filtered:

            data = []

            for guest in filtered:
                data.append({
                    "ID": guest["id"],
                    "Họ tên": guest["full_name"],
                    "Điện thoại": guest["phone"],
                    "Email": guest["email"],
                    "CCCD": guest["id_card"],
                    "Địa chỉ": guest["address"],
                })

            st.dataframe(
                pd.DataFrame(data),
                use_container_width=True,
                hide_index=True
            )

            st.divider()

            selected_guest_id = st.selectbox(
                "Chọn khách hàng để xem chi tiết",
                [
                    g["id"]
                    for g in filtered
                ],
                format_func=lambda x: next(
                    g["full_name"]
                    for g in filtered
                    if g["id"] == x
                )
            )

            selected_guest = next(
                g for g in filtered
                if g["id"] == selected_guest_id
            )

            col1, col2 = st.columns(2)

            with col1:
                st.write(
                    f"**Họ tên:** {selected_guest['full_name']}"
                )
                st.write(
                    f"**SĐT:** {selected_guest['phone']}"
                )
                st.write(
                    f"**Email:** {selected_guest['email']}"
                )

            with col2:
                st.write(
                    f"**CCCD:** {selected_guest['id_card']}"
                )
                st.write(
                    f"**Địa chỉ:** {selected_guest['address']}"
                )
                st.write(
                    f"**Ghi chú:** {selected_guest['note']}"
                )

            if st.button(
                "🗑️ Xóa khách hàng",
                type="secondary"
            ):

                booking_count = query_db(
                    """
                    SELECT COUNT(*)
                    FROM bookings
                    WHERE guest_id = ?
                    """,
                    (selected_guest_id,),
                    fetch=True
                )[0][0]

                if booking_count > 0:
                    st.error(
                        "Không thể xóa khách hàng đã có booking."
                    )
                else:
                    query_db(
                        "DELETE FROM guests WHERE id = ?",
                        (selected_guest_id,)
                    )
                    st.success("Đã xóa khách hàng.")
                    st.rerun()

        else:
            st.info("Không tìm thấy khách hàng.")


    # --------------------------------------------------------
    # THÊM KHÁCH
    # --------------------------------------------------------

    with tabs[1]:

        with st.form("add_guest_form"):

            st.subheader("➕ Thêm khách hàng")

            col1, col2 = st.columns(2)

            with col1:

                full_name = st.text_input(
                    "Họ và tên *"
                )

                phone = st.text_input(
                    "Số điện thoại"
                )

                email = st.text_input(
                    "Email"
                )

            with col2:

                id_card = st.text_input(
                    "CCCD / CMND"
                )

                address = st.text_input(
                    "Địa chỉ"
                )

                note = st.text_area(
                    "Ghi chú"
                )

            submit = st.form_submit_button(
                "➕ Thêm khách hàng",
                type="primary"
            )

            if submit:

                if not full_name.strip():
                    st.error(
                        "Vui lòng nhập họ tên."
                    )

                else:

                    query_db(
                        """
                        INSERT INTO guests
                        (
                            full_name,
                            phone,
                            email,
                            id_card,
                            address,
                            note,
                            created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            full_name,
                            phone,
                            email,
                            id_card,
                            address,
                            note,
                            datetime.now().isoformat()
                        )
                    )

                    st.success(
                        "Đã thêm khách hàng."
                    )


# ============================================================
# ĐẶT PHÒNG
# ============================================================

elif page == "📅 Đặt phòng":

    st.title("📅 Quản lý đặt phòng")

    tabs = st.tabs([
        "📋 Danh sách booking",
        "➕ Tạo booking"
    ])

    # --------------------------------------------------------
    # DANH SÁCH BOOKING
    # --------------------------------------------------------

    with tabs[0]:

        bookings = get_bookings()

        if bookings:

            for booking in bookings:

                status = booking["status"]

                with st.container(border=True):

                    col1, col2, col3, col4 = st.columns(
                        [2, 1, 2, 1]
                    )

                    col1.markdown(
                        f"### #{booking['id']} - "
                        f"{booking['full_name']}"
                    )

                    col1.write(
                        f"📞 {booking['phone'] or 'Chưa có SĐT'}"
                    )

                    col2.write(
                        f"🛏️ **Phòng {booking['room_number']}**"
                    )

                    col2.write(
                        booking["room_type"]
                    )

                    col3.write(
                        f"📅 {booking['check_in']} → "
                        f"{booking['check_out']}"
                    )

                    col3.write(
                        f"👥 {booking['adults']} người lớn, "
                        f"{booking['children']} trẻ em"
                    )

                    col4.write(
                        f"{status_color(status)} "
                        f"**{status}**"
                    )

                    col4.write(
                        f"💰 {format_money(booking['total_price'])}"
                    )

                    if booking["note"]:
                        st.caption(
                            f"📝 {booking['note']}"
                        )

                    # Thay đổi trạng thái
                    status_options = [
                        "Đã đặt",
                        "Đang ở",
                        "Đã trả",
                        "Hủy"
                    ]

                    new_status = st.selectbox(
                        "Cập nhật trạng thái",
                        status_options,
                        index=(
                            status_options.index(status)
                            if status in status_options
                            else 0
                        ),
                        key=f"status_{booking['id']}"
                    )

                    if new_status != status:

                        if st.button(
                            "💾 Cập nhật",
                            key=f"update_{booking['id']}"
                        ):

                            query_db(
                                """
                                UPDATE bookings
                                SET status = ?
                                WHERE id = ?
                                """,
                                (
                                    new_status,
                                    booking["id"]
                                )
                            )

                            # Nếu booking đang ở thì cập nhật phòng
                            room_status = "Trống"

                            if new_status == "Đang ở":
                                room_status = "Đang ở"
                            elif new_status == "Đã đặt":
                                room_status = "Đã đặt"
                            elif new_status == "Hủy":
                                room_status = "Trống"
                            elif new_status == "Đã trả":
                                room_status = "Trống"

                            query_db(
                                """
                                UPDATE rooms
                                SET status = ?
                                WHERE room_number = ?
                                """,
                                (
                                    room_status,
                                    booking["room_number"]
                                )
                            )

                            st.success(
                                "Đã cập nhật booking."
                            )

                            st.rerun()

        else:
            st.info("Chưa có booking.")


    # --------------------------------------------------------
    # TẠO BOOKING
    # --------------------------------------------------------

    with tabs[1]:

        guests = get_guests()

        available_rooms = query_db(
            """
            SELECT *
            FROM rooms
            WHERE status = 'Trống'
            ORDER BY CAST(room_number AS INTEGER)
            """,
            fetch=True
        )

        if not guests:
            st.warning(
                "Bạn cần thêm khách hàng trước khi tạo booking."
            )

        elif not available_rooms:
            st.warning(
                "Hiện không có phòng trống."
            )

        else:

            with st.form("booking_form"):

                st.subheader("➕ Tạo đặt phòng")

                guest_options = {
                    f"{g['full_name']} - "
                    f"{g['phone'] or 'Không có SĐT'}":
                    g["id"]
                    for g in guests
                }

                room_options = {
                    f"Phòng {r['room_number']} - "
                    f"{r['room_type']} - "
                    f"{format_money(r['price'])}/đêm":
                    r["id"]
                    for r in available_rooms
                }

                selected_guest = st.selectbox(
                    "Khách hàng",
                    list(guest_options.keys())
                )

                selected_room = st.selectbox(
                    "Phòng",
                    list(room_options.keys())
                )

                col1, col2 = st.columns(2)

                with col1:

                    check_in = st.date_input(
                        "Ngày check-in",
                        value=date.today()
                    )

                with col2:

                    check_out = st.date_input(
                        "Ngày check-out",
                        value=date.today()
                    )

                col1, col2 = st.columns(2)

                with col1:

                    adults = st.number_input(
                        "Người lớn",
                        min_value=1,
                        value=1
                    )

                with col2:

                    children = st.number_input(
                        "Trẻ em",
                        min_value=0,
                        value=0
                    )

                note = st.text_area(
                    "Ghi chú"
                )

                # Tính tiền
                room_id = room_options[selected_room]

                selected_room_data = next(
                    r for r in available_rooms
                    if r["id"] == room_id
                )

                nights = calculate_nights(
                    check_in,
                    check_out
                )

                total_price = (
                    selected_room_data["price"] *
                    nights
                )

                st.info(
                    f"🛏️ {nights} đêm × "
                    f"{format_money(selected_room_data['price'])}"
                    f" = **{format_money(total_price)}**"
                )

                submit_booking = st.form_submit_button(
                    "📅 Tạo booking",
                    type="primary"
                )

                if submit_booking:

                    if check_out <= check_in:

                        st.error(
                            "Ngày check-out phải sau ngày check-in."
                        )

                    else:

                        guest_id = guest_options[
                            selected_guest
                        ]

                        query_db(
                            """
                            INSERT INTO bookings
                            (
                                guest_id,
                                room_id,
                                check_in,
                                check_out,
                                adults,
                                children,
                                status,
                                total_price,
                                note,
                                created_at
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                guest_id,
                                room_id,
                                check_in.isoformat(),
                                check_out.isoformat(),
                                adults,
                                children,
                                "Đã đặt",
                                total_price,
                                note,
                                datetime.now().isoformat()
                            )
                        )

                        query_db(
                            """
                            UPDATE rooms
                            SET status = 'Đã đặt'
                            WHERE id = ?
                            """,
                            (room_id,)
                        )

                        st.success(
                            "🎉 Tạo booking thành công!"
                        )


# ============================================================
# DOANH THU
# ============================================================

elif page == "💰 Doanh thu":

    st.title("💰 Doanh thu")

    bookings = get_bookings()

    if bookings:

        df = pd.DataFrame([
            dict(b)
            for b in bookings
        ])

        df["check_in"] = pd.to_datetime(
            df["check_in"]
        )

        df["check_out"] = pd.to_datetime(
            df["check_out"]
        )

        # Không tính booking hủy
        valid_df = df[
            df["status"] != "Hủy"
        ].copy()

        total_revenue = valid_df[
            "total_price"
        ].sum()

        completed_revenue = valid_df[
            valid_df["status"] == "Đã trả"
        ]["total_price"].sum()

        pending_revenue = valid_df[
            valid_df["status"].isin(
                ["Đã đặt", "Đang ở"]
            )
        ]["total_price"].sum()

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "💰 Tổng doanh thu",
            format_money(total_revenue)
        )

        col2.metric(
            "✅ Đã hoàn tất",
            format_money(completed_revenue)
        )

        col3.metric(
            "⏳ Chưa hoàn tất",
            format_money(pending_revenue)
        )

        st.divider()

        st.subheader("📊 Doanh thu theo trạng thái")

        revenue_by_status = (
            valid_df
            .groupby("status")["total_price"]
            .sum()
        )

        st.bar_chart(
            revenue_by_status
        )

        st.divider()

        st.subheader("📋 Chi tiết doanh thu")

        revenue_table = valid_df[
            [
                "id",
                "full_name",
                "room_number",
                "check_in",
                "check_out",
                "status",
                "total_price"
            ]
        ].copy()

        revenue_table["total_price"] = (
            revenue_table["total_price"]
            .apply(format_money)
        )

        revenue_table.columns = [
            "Booking",
            "Khách hàng",
            "Phòng",
            "Check-in",
            "Check-out",
            "Trạng thái",
            "Doanh thu"
        ]

        st.dataframe(
            revenue_table,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info(
            "Chưa có dữ liệu doanh thu."
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "🏨 Hotel Manager • Streamlit • SQLite"
)
