import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Minimalist Bej va Jigarrang rang palitrasi:
COLOR_BG = (245, 241, 235)           # Asosiy yumshoq bej (#F5F1EB)
COLOR_CARD_BG = (250, 247, 242)      # Ichki kartochka och krem-bej (#FAF7F2)
COLOR_BORDER = (212, 199, 184)       # Nozik bej hoshiya (#D4C7B8)
COLOR_PRIMARY = (59, 40, 27)         # To'q kofe jigarrang sarlavhalar (#3B281B)
COLOR_SECONDARY = (116, 92, 73)      # O'rtacha yong'oq jigarrang matn (#745C49)
COLOR_ACCENT = (158, 107, 66)        # Iliq karamel-jigarrang urg'u (#9E6B42)
COLOR_MUTED = (140, 119, 101)        # Xira och jigarrang (#8C7765)

def get_font(size: int, bold: bool = False):
    """Windows tizimidagi shriftlarni yuklaydi."""
    font_names = [
        "seguisb.ttf" if bold else "segoeui.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
        "calibrib.ttf" if bold else "calibri.ttf",
        # Linux (Docker / Railway) shriftlari
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for fn in font_names:
        try:
            return ImageFont.truetype(fn, size)
        except Exception:
            continue
    return ImageFont.load_default()


def generate_welcome_card(
    name: str = "Foydalanuvchi",
    date_str: str = None,
    output_path: str = "downloads/welcome_card.png"
) -> str:
    """
    Botga kirganda ko'rinadigan asosiy bej va jigarrang muqova kartochkasi.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    date_str = date_str or datetime.now().strftime("%d.%m.%Y")

    width, height = 800, 420
    img = Image.new("RGB", (width, height), COLOR_BG)
    draw = ImageDraw.Draw(img)

    # Tashqi nozik hoshiya
    draw.rounded_rectangle(
        [(20, 20), (width - 20, height - 20)],
        radius=16,
        fill=None,
        outline=COLOR_BORDER,
        width=2
    )

    font_brand = get_font(13, bold=True)
    font_title = get_font(30, bold=True)
    font_sub = get_font(16, bold=False)
    font_col_title = get_font(12, bold=True)
    font_col_desc = get_font(14, bold=False)
    font_footer = get_font(12, bold=False)

    # Sarlavha qismi
    draw.text((48, 44), "SMART OFFICE ASSISTANT", fill=COLOR_ACCENT, font=font_brand)
    draw.text((48, 68), "XUSH KELIBSIZ", fill=COLOR_PRIMARY, font=font_title)
    clean_name = name if len(name) <= 30 else name[:27] + "..."
    draw.text((48, 114), f"Foydalanuvchi: {clean_name}  ·  Sana: {date_str}", fill=COLOR_SECONDARY, font=font_sub)

    # Ajratuvchi chiziq
    draw.line([(48, 146), (width - 48, 146)], fill=COLOR_BORDER, width=1)

    # 3 ta xizmat ustuni
    cols = [
        ("DAVOMAT", "Wi-Fi orqali avtomatik kelish va ketish hisobi"),
        ("HUJJATLAR", "PDF, Word, Excel va arxivlar xavfsiz saqlash"),
        ("ESLATMALAR", "Muhim ish topshiriqlari va rejalashtirish")
    ]
    col_w = 218
    col_y = 170
    col_h = 145

    for i, (c_title, c_desc) in enumerate(cols):
        cx = 48 + i * (col_w + 25)
        draw.rounded_rectangle(
            [(cx, col_y), (cx + col_w, col_y + col_h)],
            radius=12,
            fill=COLOR_CARD_BG,
            outline=COLOR_BORDER,
            width=1
        )
        draw.text((cx + 18, col_y + 20), c_title, fill=COLOR_PRIMARY, font=font_col_title)
        draw.line([(cx + 18, col_y + 40), (cx + 50, col_y + 40)], fill=COLOR_ACCENT, width=2)

        # Matnni qatorlarga bo'lish
        words = c_desc.split()
        lines = []
        cur_line = []
        for w in words:
            if len(" ".join(cur_line + [w])) <= 22:
                cur_line.append(w)
            else:
                lines.append(" ".join(cur_line))
                cur_line = [w]
        if cur_line:
            lines.append(" ".join(cur_line))

        ly = col_y + 58
        for line in lines[:3]:
            draw.text((cx + 18, ly), line, fill=COLOR_SECONDARY, font=font_col_desc)
            ly += 22

    # Pastki qism
    draw.line([(48, 348), (width - 48, 348)], fill=COLOR_BORDER, width=1)
    draw.text((48, 366), "MINIMALISTIK BOSHQARUV TIZIMI", fill=COLOR_MUTED, font=font_footer)
    draw.text((width - 240, 366), "BEJ VA JIGARRANG DIZAYN", fill=COLOR_MUTED, font=font_footer)

    img.save(output_path, "PNG", quality=95)
    return output_path


def generate_checkin_card(
    time_str: str = "08:50",
    method_str: str = "Wi-Fi avtomat",
    date_str: str = None,
    output_path: str = "downloads/checkin_card.png"
) -> str:
    """Kelish qayd etilganda bej-jigarrang kartochka."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    date_str = date_str or datetime.now().strftime("%d.%m.%Y")
    width, height = 800, 320
    img = Image.new("RGB", (width, height), COLOR_BG)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([(20, 20), (width - 20, height - 20)], radius=16, fill=None, outline=COLOR_BORDER, width=2)
    font_brand = get_font(13, bold=True)
    font_title = get_font(26, bold=True)
    font_val = get_font(48, bold=True)
    font_sub = get_font(14, bold=False)

    draw.text((48, 40), "DAVOMAT TIZIMI", fill=COLOR_ACCENT, font=font_brand)
    draw.text((48, 64), "KELISH QAYD ETILDI", fill=COLOR_PRIMARY, font=font_title)
    draw.text((48, 102), f"Sana: {date_str}  ·  Usul: {method_str}", fill=COLOR_SECONDARY, font=font_sub)

    # Vaqt qutisi
    draw.rounded_rectangle([(48, 140), (width - 48, 260)], radius=12, fill=COLOR_CARD_BG, outline=COLOR_BORDER, width=1)
    draw.text((74, 156), "KELGAN VAQTINGIZ", fill=COLOR_SECONDARY, font=get_font(12, bold=True))
    draw.text((74, 180), time_str, fill=COLOR_PRIMARY, font=font_val)

    draw.text((width - 290, 195), "Kuningiz unumli o'tsin", fill=COLOR_MUTED, font=font_sub)

    img.save(output_path, "PNG", quality=95)
    return output_path


def generate_checkout_card(
    check_in: str = "--:--",
    check_out: str = "--:--",
    duration: str = "0s 0d",
    date_str: str = None,
    output_path: str = "downloads/checkout_card.png"
) -> str:
    """Ketish qayd etilganda bej-jigarrang kartochka."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    date_str = date_str or datetime.now().strftime("%d.%m.%Y")
    width, height = 800, 360
    img = Image.new("RGB", (width, height), COLOR_BG)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([(20, 20), (width - 20, height - 20)], radius=16, fill=None, outline=COLOR_BORDER, width=2)
    font_brand = get_font(13, bold=True)
    font_title = get_font(26, bold=True)
    font_val = get_font(38, bold=True)
    font_sub = get_font(14, bold=False)

    draw.text((48, 38), "DAVOMAT TIZIMI", fill=COLOR_ACCENT, font=font_brand)
    draw.text((48, 62), "ISH KUNI YAKUNLANDI", fill=COLOR_PRIMARY, font=font_title)
    draw.text((48, 98), f"Sana: {date_str}  ·  Yaxshi dam oling", fill=COLOR_SECONDARY, font=font_sub)

    # 3 ta quti
    bw = 218
    by = 135
    bh = 160
    items = [
        ("KELISH", check_in, COLOR_PRIMARY),
        ("KETISH", check_out, COLOR_PRIMARY),
        ("ISHLANGAN VAQT", duration, COLOR_ACCENT)
    ]
    for i, (lbl, val, col) in enumerate(items):
        bx = 48 + i * (bw + 25)
        draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=12, fill=COLOR_CARD_BG, outline=COLOR_BORDER, width=1)
        draw.text((bx + 18, by + 18), lbl, fill=COLOR_SECONDARY, font=get_font(12, bold=True))
        draw.line([(bx + 18, by + 40), (bx + 50, by + 40)], fill=COLOR_ACCENT, width=2)
        draw.text((bx + 18, by + 68), val, fill=col, font=font_val)

    img.save(output_path, "PNG", quality=95)
    return output_path


def generate_attendance_card(
    title: str = "ISH VAQTI QAYDI",
    date_str: str = None,
    check_in: str = "--:--",
    check_out: str = "--:--",
    duration: str = "Hali yakunlanmadi",
    status_text: str = "Faol ish vaqti",
    output_path: str = "downloads/attendance_card.png"
) -> str:
    """Minimalistik bej va jigarrang oylik/kunlik hisobot kartochkasi."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    date_str = date_str or datetime.now().strftime("%d.%m.%Y")

    width, height = 800, 420
    img = Image.new("RGB", (width, height), COLOR_BG)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([(20, 20), (width - 20, height - 20)], radius=16, fill=None, outline=COLOR_BORDER, width=2)

    font_header = get_font(26, bold=True)
    font_sub = get_font(15, bold=False)
    font_box_title = get_font(13, bold=True)
    font_box_value = get_font(32, bold=True)
    font_footer = get_font(13, bold=False)

    draw.text((48, 46), title.upper(), fill=COLOR_PRIMARY, font=font_header)
    draw.text((48, 82), f"Sana: {date_str}  ·  Holat: {status_text}", fill=COLOR_SECONDARY, font=font_sub)
    draw.line([(48, 116), (width - 48, 116)], fill=COLOR_BORDER, width=1)

    box_w = 218
    box_h = 170
    box_y = 140
    boxes = [
        ("KELISH VAQTI", check_in, COLOR_PRIMARY),
        ("KETISH VAQTI", check_out, COLOR_PRIMARY),
        ("ISHLANGAN VAQT", duration, COLOR_ACCENT)
    ]

    for i, (b_title, b_val, val_color) in enumerate(boxes):
        bx = 48 + i * (box_w + 25)
        draw.rounded_rectangle([(bx, box_y), (bx + box_w, box_y + box_h)], radius=12, fill=COLOR_CARD_BG, outline=COLOR_BORDER, width=1)
        draw.text((bx + 20, box_y + 24), b_title, fill=COLOR_SECONDARY, font=font_box_title)
        draw.line([(bx + 20, box_y + 48), (bx + 60, box_y + 48)], fill=COLOR_ACCENT, width=2)
        draw.text((bx + 20, box_y + 76), b_val, fill=val_color, font=font_box_value)

    draw.line([(48, 345), (width - 48, 345)], fill=COLOR_BORDER, width=1)
    draw.text((48, 362), "SMART OFFICE ASSISTANT", fill=COLOR_MUTED, font=font_footer)
    draw.text((width - 240, 362), "SHAXSIY VAQT BOSHQARUVI", fill=COLOR_MUTED, font=font_footer)

    img.save(output_path, "PNG", quality=95)
    return output_path


def generate_location_card(
    road: str = "",
    district: str = "",
    time_str: str = "--:--",
    output_path: str = "downloads/location_card.png"
) -> str:
    """Minimalistik bej va jigarrang joriy joylashuv kartochkasi."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    width, height = 800, 340
    img = Image.new("RGB", (width, height), COLOR_BG)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([(20, 20), (width - 20, height - 20)], radius=16, fill=None, outline=COLOR_BORDER, width=2)
    font_brand = get_font(13, bold=True)
    font_title = get_font(26, bold=True)
    font_road = get_font(26, bold=True)
    font_sub = get_font(15, bold=False)

    draw.text((48, 38), "GPS JONLI KUZATUV", fill=COLOR_ACCENT, font=font_brand)
    draw.text((48, 62), "JORIY JOYLASHUVINGIZ", fill=COLOR_PRIMARY, font=font_title)
    draw.text((48, 98), f"Yangilangan vaqt: {time_str}  ·  Real vaqt rejimi", fill=COLOR_SECONDARY, font=font_sub)

    # Manzil qutisi
    draw.rounded_rectangle([(48, 135), (width - 48, 280)], radius=12, fill=COLOR_CARD_BG, outline=COLOR_BORDER, width=1)
    clean_road = road if road else "Ko'cha aniqlanmoqda..."
    if len(clean_road) > 38:
        clean_road = clean_road[:35] + "..."

    clean_dist = district if district else "Toshkent"
    if len(clean_dist) > 42:
        clean_dist = clean_dist[:39] + "..."

    draw.text((74, 155), "KO'CHA", fill=COLOR_SECONDARY, font=get_font(12, bold=True))
    draw.text((74, 178), clean_road, fill=COLOR_PRIMARY, font=font_road)

    draw.text((74, 222), "HUDUD / TUMAN", fill=COLOR_SECONDARY, font=get_font(12, bold=True))
    draw.text((74, 242), clean_dist, fill=COLOR_SECONDARY, font=font_sub)

    img.save(output_path, "PNG", quality=95)
    return output_path


def generate_street_change_card(
    old_street: str = "",
    new_street: str = "",
    district: str = "",
    time_str: str = "--:--",
    output_path: str = "downloads/street_change.png"
) -> str:
    """Ko'cha o'zgarganda bej va jigarrang xabarnoma kartochkasi."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    width, height = 800, 380
    img = Image.new("RGB", (width, height), COLOR_BG)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([(20, 20), (width - 20, height - 20)], radius=16, fill=None, outline=COLOR_BORDER, width=2)
    font_brand = get_font(13, bold=True)
    font_title = get_font(26, bold=True)
    font_label = get_font(12, bold=True)
    font_street = get_font(20, bold=True)
    font_sub = get_font(14, bold=False)

    draw.text((48, 36), "HARAKATLANISH YO'NALISHI", fill=COLOR_ACCENT, font=font_brand)
    draw.text((48, 60), "KO'CHA O'ZGARDI", fill=COLOR_PRIMARY, font=font_title)
    clean_dist = district if district else "Toshkent"
    draw.text((48, 96), f"Vaqt: {time_str}  ·  Hudud: {clean_dist}", fill=COLOR_SECONDARY, font=font_sub)

    # 1-quti: Avvalgi ko'cha
    draw.rounded_rectangle([(48, 130), (370, 290)], radius=12, fill=COLOR_CARD_BG, outline=COLOR_BORDER, width=1)
    draw.text((68, 150), "AVVALGI KO'CHA", fill=COLOR_MUTED, font=font_label)
    clean_old = old_street if old_street else "Boshlang'ich ko'cha"
    if len(clean_old) > 28:
        clean_old = clean_old[:25] + "..."
    draw.text((68, 185), clean_old, fill=COLOR_SECONDARY, font=font_street)

    # O'rtadagi belgi
    draw.text((388, 195), "->", fill=COLOR_ACCENT, font=get_font(24, bold=True))

    # 2-quti: Yangi ko'cha
    draw.rounded_rectangle([(430, 130), (width - 48, 290)], radius=12, fill=COLOR_CARD_BG, outline=COLOR_BORDER, width=1)
    draw.text((450, 150), "YANGI KO'CHA", fill=COLOR_ACCENT, font=font_label)
    clean_new = new_street if new_street else "Yangi ko'cha"
    if len(clean_new) > 28:
        clean_new = clean_new[:25] + "..."
    draw.text((450, 185), clean_new, fill=COLOR_PRIMARY, font=font_street)

    draw.text((48, 330), "SMART OFFICE ASSISTANT · AVTOMATIK KUZATUV", fill=COLOR_MUTED, font=get_font(12, bold=False))

    img.save(output_path, "PNG", quality=95)
    return output_path


