import tempfile
import urllib.parse

import aiohttp
import gradio as gr
from anyio import Path, open_file

API_ENDPOINT = "http://localhost:8080/api/upload"

ALLOWED_SUFFIXES = [".xlsx"]

async def upload_excel(file_path: str) -> tuple[str, str | None, str]:  # noqa: PLR0911
    if file_path is None:
        return "Пожалуйста, загрузите файл.", None, ""

    apath = Path(file_path)

    if not await apath.exists():
        return "Файл не найден.", None, ""

    suffix = apath.name.rsplit(".", 1)[-1]
    suffix = f".{suffix.lower()}"
    if suffix not in ALLOWED_SUFFIXES:
        return (
            "Поддерживаются только файлы формата "
            f"{', '.join(ALLOWED_SUFFIXES)}.",
            None,
            ""
        )

    try:
        async with await open_file(file_path, "rb") as f:
            file_bytes = await f.read()

        # filename = str(await apath).rsplit("/", 1)[-1]
        filename = apath.name

        timeout = aiohttp.ClientTimeout(total=2400) # 40 минут таймаут
        async with aiohttp.ClientSession(timeout=timeout) as session:
            form = aiohttp.FormData()
            form.add_field(
                "file",
                file_bytes,
                filename=filename,
                content_type="application/octet-stream",
            )
            async with session.post(API_ENDPOINT, data=form) as response:
                if response.status != 200: # noqa: PLR2004
                    body = await response.text()
                    return (
                        "❌ Сервер вернул ошибку: HTTP "
                        f"{response.status}\n{body[:500]}",
                        None,
                        ""
                    )

                content_disposition = response.headers.get(
                    "Content-Disposition", ""
                )
                content_type = response.headers.get(
                    "Content-Type",
                    "application/octet-stream"
                )

                raw_summary = response.headers.get("X-Summary", "")
                grand_summary = (
                    urllib.parse.unquote_plus(raw_summary)
                    if raw_summary else "Выжимка не найдена."
                )
                resp_bytes = await response.read()

        out_filename = "result.zip"
        if "filename=" in content_disposition:
            out_filename = content_disposition.split(
                "filename="
            )[-1].strip().strip('"')
        elif "csv" in content_type:
            out_filename = "result.csv"

        tmp_dir = Path(tempfile.mkdtemp())
        out_path = tmp_dir / out_filename

        async with await open_file(out_path, "wb") as f:
            await f.write(resp_bytes)

        return (
            "✅ Файл успешно обработан! Размер ответа: "
            f"{len(resp_bytes):,} байт.",
            str(out_path),
            grand_summary
        )

    except aiohttp.ClientConnectorError:
        return (
            f"❌ Не удалось подключиться к серверу: {API_ENDPOINT}\n"
            "Убедитесь, что сервер запущен.",
            None,
            ""
        )
    except TimeoutError:
        return (
            "❌ Превышено время ожидания ответа от сервера (30 мин).",
            None, ""
        )
    except Exception as e: # noqa: BLE001
        return f"❌ Непредвиденная ошибка: {type(e).__name__}: {e}", None, ""



with gr.Blocks(
    title="Excel Upload Service",
    theme=gr.themes.Soft(),
    css="""
        .upload-box { border: 2px dashed #4f8ef7 !important; border-radius: 12px !important; }
        .status-box textarea { font-size: 15px !important; }
        footer { display: none !important; }
        .file-output-hidden { display: none !important; }
        #download-btn { display: none; }
        #download-btn.visible {
            display: flex !important;
            align-items: center;
            justify-content: center;
            gap: 8px;
            width: 30%;
            padding: 12px 20px;
            background: #4f46e5;
            color: white !important;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            transition: background 0.2s;
        }
        #download-btn.visible:hover { background: #6366f1; }
    """,  # noqa: E501
) as demo:

    gr.Markdown(
        f"""
        # 📊 Excel Upload Service
        ### Загрузите файл для обработки. Поддерживаемые форматы: {", ".join(ALLOWED_SUFFIXES)}
        """  # noqa: E501
    )

    with gr.Row(scale=2):
        with gr.Column(scale=1):
            file_input = gr.File(
                label="Выберите файл",
                file_types=ALLOWED_SUFFIXES,
                elem_classes=["upload-box"],
            )
            submit_btn = gr.Button(
                "Отправить",
                variant="primary",
                size="lg"
            )

        with gr.Column(scale=1):
            status_output = gr.Textbox(
                label="Статус",
                interactive=False,
                elem_classes=["status-box"],
                lines=3,
            )

    summary_output = gr.Textbox(
        label="Главная аналитическая выжимка",
        interactive=False,
        lines=5,
    )

    file_output = gr.File(
        label="Скачать результат",
        interactive=False,
        visible=True,
        elem_classes=["file-output-hidden"],
    )

    gr.HTML(
        '<div style="display:flex; justify-content:center;">'
        '<a id="download-btn">Скачать архив с результатами</a></div>'
    )

    file_output.change(
        fn=None,
        inputs=None,
        outputs=None,
        js="""
        () => {
            const poll = setInterval(() => {
                const anchor = document.querySelector('.file-output-hidden a[href]');
                const btn = document.getElementById('download-btn');
                if (!btn) return;
                if (anchor && anchor.href) {
                    btn.href = anchor.href;
                    btn.download = anchor.getAttribute('download') || 'analytics_pack.zip';
                    btn.classList.add('visible');
                    clearInterval(poll);
                } else {
                    btn.classList.remove('visible');
                }
            }, 100);
        }
        """, # noqa: E501
    )

    submit_btn.click(
        fn=lambda: (
            gr.update(value=(
                "⏳ Загрузка и обработка файла "
                "(может занять до 15 минут)..."
            )),
            gr.update(value=None),
            gr.update(value="")
        ),
        inputs=None,
        outputs=[status_output, file_output, summary_output],
        queue=False,
    ).then(
        fn=upload_excel,
        inputs=[file_input],
        outputs=[status_output, file_output, summary_output],
        queue=True,
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=80,
        max_file_size="10gb"
    )
