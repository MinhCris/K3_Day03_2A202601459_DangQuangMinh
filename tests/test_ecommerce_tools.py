import unittest

from src.tools.ecommerce import (
    calc_shipping,
    calculate_order_total,
    check_stock,
    get_discount,
)


class EcommerceToolTests(unittest.TestCase):
    def test_check_stock_returns_price_weight_and_quantity(self):
        result = check_stock("iPhone 15")
        self.assertTrue(result["found"])
        self.assertEqual(result["available_quantity"], 5)
        self.assertEqual(result["unit_price_vnd"], 22_990_000)

    def test_invalid_coupon_has_zero_discount(self):
        result = get_discount("not-real")
        self.assertFalse(result["valid"])
        self.assertEqual(result["discount_percent"], 0)

    def test_hanoi_shipping_under_one_kg_uses_base_fee(self):
        result = calc_shipping(0.342, "Hanoi")
        self.assertTrue(result["supported"])
        self.assertEqual(result["shipping_fee_vnd"], 30_000)

    def test_total_calculation_is_transparent(self):
        result = calculate_order_total(22_990_000, 2, 10, 30_000)
        self.assertEqual(result["subtotal_vnd"], 45_980_000)
        self.assertEqual(result["discount_amount_vnd"], 4_598_000)
        self.assertEqual(result["total_vnd"], 41_412_000)


if __name__ == "__main__":
    unittest.main()
