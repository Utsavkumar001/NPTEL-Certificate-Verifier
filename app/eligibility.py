def calculate_credits(weeks):
    """12 weeks → 4 credits, 8 weeks → 3 credits, 4 weeks → 2 credits."""
    credit_map = {12: 4, 8: 3, 4: 2}
    return credit_map.get(weeks, 0)