from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont


CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1350

BACKGROUND = (246, 247, 249)
CARD = (255, 255, 255)
TEXT = (28, 31, 35)
MUTED = (105, 112, 122)
GREEN = (24, 160, 88)
RED = (214, 55, 55)
DARK = (17, 24, 39)


def _font_candidates(
    bold: bool = False,
) -> list[Path]:
    windows_fonts = Path(
        "C:/Windows/Fonts"
    )

    if bold:
        names = [
            "arialbd.ttf",
            "segoeuib.ttf",
            "calibrib.ttf",
        ]
    else:
        names = [
            "arial.ttf",
            "segoeui.ttf",
            "calibri.ttf",
        ]

    candidates = [
        windows_fonts / name
        for name in names
    ]

    if bold:
        candidates.extend(
            [
                Path(
                    "/usr/share/fonts/truetype/"
                    "dejavu/DejaVuSans-Bold.ttf"
                ),
                Path(
                    "/usr/share/fonts/truetype/"
                    "liberation2/"
                    "LiberationSans-Bold.ttf"
                ),
            ]
        )
    else:
        candidates.extend(
            [
                Path(
                    "/usr/share/fonts/truetype/"
                    "dejavu/DejaVuSans.ttf"
                ),
                Path(
                    "/usr/share/fonts/truetype/"
                    "liberation2/"
                    "LiberationSans-Regular.ttf"
                ),
            ]
        )

    return candidates


def _font(
    size: int,
    bold: bool = False,
) -> ImageFont.ImageFont:
    for path in _font_candidates(
        bold=bold
    ):
        if path.exists():
            return ImageFont.truetype(
                str(path),
                size=size,
            )

    return ImageFont.load_default()


def _format_price(
    value: Any,
) -> str:
    try:
        number = float(value)

    except (TypeError, ValueError):
        number = 0

    return (
        f"{number:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def _load_product_image(
    url: str,
    size: tuple[int, int],
) -> Image.Image | None:
    if not url:
        return None

    try:
        request = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64)"
                )
            },
        )

        with urlopen(
            request,
            timeout=8,
        ) as response:
            raw = response.read()

        product_image = Image.open(
            BytesIO(raw)
        ).convert("RGB")

        product_image.thumbnail(
            size,
            Image.Resampling.LANCZOS,
        )

        canvas = Image.new(
            "RGB",
            size,
            CARD,
        )

        x = (
            size[0]
            - product_image.width
        ) // 2

        y = (
            size[1]
            - product_image.height
        ) // 2

        canvas.paste(
            product_image,
            (x, y),
        )

        return canvas

    except Exception:
        return None


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    max_lines: int,
) -> list[str]:
    words = str(text).split()

    lines: list[str] = []
    current = ""

    for word in words:
        candidate = (
            f"{current} {word}".strip()
        )

        box = draw.textbbox(
            (0, 0),
            candidate,
            font=font,
        )

        text_width = (
            box[2] - box[0]
        )

        if text_width <= max_width:
            current = candidate
            continue

        if current:
            lines.append(current)

        current = word

        if len(lines) >= max_lines:
            break

    if (
        current
        and len(lines) < max_lines
    ):
        lines.append(current)

    if len(lines) == max_lines:
        last_line = lines[-1]

        while last_line:
            candidate = (
                last_line.rstrip(" .")
                + "..."
            )

            box = draw.textbbox(
                (0, 0),
                candidate,
                font=font,
            )

            if (
                box[2] - box[0]
                <= max_width
            ):
                lines[-1] = candidate
                break

            last_line = last_line[:-1]

    return lines


def create_deal_image(
    product: dict,
) -> bytes:
    image = Image.new(
        "RGB",
        (
            CANVAS_WIDTH,
            CANVAS_HEIGHT,
        ),
        BACKGROUND,
    )

    draw = ImageDraw.Draw(image)

    title_font = _font(
        48,
        bold=True,
    )

    product_font = _font(
        44,
        bold=True,
    )

    label_font = _font(
        29,
    )

    old_price_font = _font(
        38,
    )

    current_price_font = _font(
        65,
        bold=True,
    )

    badge_font = _font(
        31,
        bold=True,
    )

    footer_font = _font(
        24,
    )

    margin = 60

    draw.rounded_rectangle(
        (
            margin,
            45,
            CANVAS_WIDTH - margin,
            150,
        ),
        radius=28,
        fill=DARK,
    )

    draw.text(
        (
            margin + 35,
            72,
        ),
        "🔥 GÜNÜN FIRSATI",
        font=title_font,
        fill=(255, 255, 255),
    )

    image_box = (
        margin,
        185,
        CANVAS_WIDTH - margin,
        665,
    )

    draw.rounded_rectangle(
        image_box,
        radius=34,
        fill=CARD,
    )

    product_image = (
        _load_product_image(
            str(
                product.get("image")
                or ""
            ),
            (
                image_box[2]
                - image_box[0]
                - 40,
                image_box[3]
                - image_box[1]
                - 40,
            ),
        )
    )

    if product_image:
        x = (
            image_box[0]
            + (
                image_box[2]
                - image_box[0]
                - product_image.width
            )
            // 2
        )

        y = (
            image_box[1]
            + (
                image_box[3]
                - image_box[1]
                - product_image.height
            )
            // 2
        )

        image.paste(
            product_image,
            (x, y),
        )

    else:
        draw.text(
            (
                CANVAS_WIDTH // 2,
                420,
            ),
            "Ürün görseli yok",
            anchor="mm",
            font=label_font,
            fill=MUTED,
        )

    name_lines = _wrap_text(
        draw=draw,
        text=(
            product.get("name")
            or "Ürün"
        ),
        font=product_font,
        max_width=(
            CANVAS_WIDTH
            - margin * 2
        ),
        max_lines=3,
    )

    y = 705

    for line in name_lines:
        draw.text(
            (
                margin,
                y,
            ),
            line,
            font=product_font,
            fill=TEXT,
        )

        y += 57

    y += 18

    previous_price = _format_price(
        product.get(
            "previous_price"
        )
    )

    current_price = _format_price(
        product.get("price")
    )

    price_difference = (
        _format_price(
            product.get(
                "price_difference"
            )
        )
    )

    price_drop = float(
        product.get("price_drop")
        or 0
    )

    draw.text(
        (
            margin,
            y,
        ),
        "Önceki fiyat",
        font=label_font,
        fill=MUTED,
    )

    y += 42

    old_price_text = (
        f"{previous_price} TL"
    )

    draw.text(
        (
            margin,
            y,
        ),
        old_price_text,
        font=old_price_font,
        fill=MUTED,
    )

    old_box = draw.textbbox(
        (
            margin,
            y,
        ),
        old_price_text,
        font=old_price_font,
    )

    strike_y = (
        old_box[1]
        + old_box[3]
    ) // 2

    draw.line(
        (
            old_box[0],
            strike_y,
            old_box[2],
            strike_y,
        ),
        fill=RED,
        width=5,
    )

    y += 68

    draw.text(
        (
            margin,
            y,
        ),
        f"{current_price} TL",
        font=current_price_font,
        fill=GREEN,
    )

    badge_y = y + 100

    drop_text = (
        f"%{price_drop:.0f} İNDİRİM"
    )

    saving_text = (
        f"{price_difference} TL KAZANÇ"
    )

    drop_box = draw.textbbox(
        (0, 0),
        drop_text,
        font=badge_font,
    )

    drop_width = (
        drop_box[2]
        - drop_box[0]
        + 54
    )

    draw.rounded_rectangle(
        (
            margin,
            badge_y,
            margin + drop_width,
            badge_y + 64,
        ),
        radius=22,
        fill=RED,
    )

    draw.text(
        (
            margin + 27,
            badge_y + 14,
        ),
        drop_text,
        font=badge_font,
        fill=(255, 255, 255),
    )

    saving_x = (
        margin
        + drop_width
        + 20
    )

    saving_box = draw.textbbox(
        (0, 0),
        saving_text,
        font=badge_font,
    )

    saving_width = (
        saving_box[2]
        - saving_box[0]
        + 54
    )

    draw.rounded_rectangle(
        (
            saving_x,
            badge_y,
            min(
                saving_x
                + saving_width,
                CANVAS_WIDTH
                - margin,
            ),
            badge_y + 64,
        ),
        radius=22,
        fill=GREEN,
    )

    draw.text(
        (
            saving_x + 27,
            badge_y + 14,
        ),
        saving_text,
        font=badge_font,
        fill=(255, 255, 255),
    )

    footer_y = (
        CANVAS_HEIGHT - 112
    )

    draw.line(
        (
            margin,
            footer_y - 28,
            CANVAS_WIDTH - margin,
            footer_y - 28,
        ),
        fill=(220, 224, 229),
        width=2,
    )

    seller = (
        product.get("seller")
        or "Bilinmiyor"
    )

    score = int(
        product.get(
            "opportunity_score"
        )
        or 0
    )

    footer_text = (
        f"Satıcı: {seller}   •   "
        f"Fırsat puanı: {score}/100"
    )

    draw.text(
        (
            margin,
            footer_y,
        ),
        footer_text,
        font=footer_font,
        fill=MUTED,
    )

    output = BytesIO()

    image.save(
        output,
        format="PNG",
        optimize=True,
    )

    return output.getvalue()