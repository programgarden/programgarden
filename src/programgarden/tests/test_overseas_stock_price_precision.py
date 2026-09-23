from programgarden.executor import ls_overseas_stock_limit_price


def test_buy_rounds_up_to_the_cent_at_or_above_one_dollar():
    assert ls_overseas_stock_limit_price(2.055, "buy") == 2.06
    assert ls_overseas_stock_limit_price(2.051, "buy") == 2.06
    assert ls_overseas_stock_limit_price(2.05, "buy") == 2.05


def test_sell_rounds_down_to_the_cent_at_or_above_one_dollar():
    assert ls_overseas_stock_limit_price(2.055, "sell") == 2.05
    assert ls_overseas_stock_limit_price(337.615, "SELL") == 337.61


def test_sub_dollar_prices_pass_through_unchanged():
    assert ls_overseas_stock_limit_price(0.8625, "buy") == 0.8625
    assert ls_overseas_stock_limit_price(0.99, "sell") == 0.99


def test_exact_cent_prices_are_unchanged_for_both_sides():
    assert ls_overseas_stock_limit_price(150.0, "buy") == 150.0
    assert ls_overseas_stock_limit_price(1.44, "sell") == 1.44
