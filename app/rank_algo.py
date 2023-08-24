from app.models import Account, Interaction, AccountActivity, InteractionType
from datetime import datetime, timedelta
from sqlalchemy import and_


def rank_companies():
    # Fetch all accounts
    import main
    from main import app
    with app.app_context():
        all_accounts = Account.query.all()

    # Initialize an empty list to store the ranked companies
    ranked_companies = []

    # Fetch closed won and open opportunities
    closed_opps = main.get_closed_won_opps()
    open_opps = main.get_open_opps()

    # Organize opportunities by account.Id
    open_opps_by_account = {opp["node"]["Account"]["Id"]: +1 for opp in open_opps}
    closed_opps_by_account = {opp["node"]["Account"]["Id"]: +1 for opp in closed_opps}

    for account in all_accounts:
        account_id = account.Id

        # Fetch the last interaction for the account
        interaction = Interaction.query.filter_by(account_id=account_id).order_by(
            Interaction.timestamp.desc()).first()

        # Determine rank based on criteria
        if account_id in open_opps_by_account:
            rank = 1
        elif account_id in closed_opps_by_account:
            rank = 2
        elif interaction:  # If there is any interaction
            rank = 3
        else:
            rank = 4

        # Append the company and its rank
        ranked_companies.append((account, rank))

    # Sort companies based on rank
    ranked_companies.sort(key=lambda x: x[1])

    return ranked_companies


def normalize(value, min_val, max_val):
    """
    Normalize a value using Min-Max normalization.
    """
    if max_val == min_val:  # Avoid division by zero
        return 1  # or return 0, depending on your requirements
    return (value - min_val) / (max_val - min_val)
