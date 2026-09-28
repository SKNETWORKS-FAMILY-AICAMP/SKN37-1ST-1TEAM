from db.connection import fetch_all

def get_car_info() -> list[dict]:
    """car_info 테이블 전체를 읽어온다."""
    return fetch_all(
        "SELECT id, brand, car_name, car_type, fuel_type, price_str, price_num, avg_efficiency "
        "FROM car_info"
    )