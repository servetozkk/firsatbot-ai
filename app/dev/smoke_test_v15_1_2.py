from pathlib import Path
import ast

TARGET = "/api/multi-store-repair/v14/products/{global_product_id}"


def ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


def count_target_routes(text: str):
    module = ast.parse(text)
    names = []

    for node in module.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue

            func = decorator.func
            if not (
                isinstance(func, ast.Attribute)
                and func.attr == "post"
                and decorator.args
            ):
                continue

            arg = decorator.args[0]
            if isinstance(arg, ast.Constant) and arg.value == TARGET:
                names.append(node.name)

    return len(names), names


def main() -> int:
    root = Path.cwd()
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    ok(version == "15.1.2", "VERSION 15.1.2")

    main_path = root / "main.py"
    main_text = main_path.read_text(encoding="utf-8")

    count, names = count_target_routes(main_text)

    ok(count == 1, f"çok mağazalı POST route tek kayıt: {names}")
    ok(
        names == ["canonical_multi_store_repair_v1512"],
        "kanonik route fonksiyonu aktif",
    )
    ok(
        "V15_1_2_CANONICAL_MULTI_STORE_API" in main_text,
        "v15.1.2 kanonik route işareti mevcut",
    )
    ok(
        "GLOBAL_PRODUCT_SOURCE_NOT_FOUND" in main_text,
        "404 durumunda açıklayıcı hata gövdesi mevcut",
    )
    ok(
        "candidate_limit: int = 50" in main_text,
        "aday limiti 50 korunuyor",
    )

    print(
        "\nFırsatAI v15.1.2 Çok Mağazalı Route "
        "Tekilleştirme smoke test başarılı."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
