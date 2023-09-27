from app.models import Account, Interaction, AccountActivity, InteractionType
from datetime import datetime, timedelta
from sqlalchemy import and_


from collections import defaultdict

def rank_companies():
    # Fetch all accounts
    import main
    from main import app
    with app.app_context():
        all_accounts = Account.query.all()

    # Fetch closed won opportunities
    closed_opps = main.get_closed_won_opps()
    open_opps = main.get_open_opps()

    # Compute scores
    scores = defaultdict(int)

    # Scoring for closed won opportunities
    closed_opps_count = defaultdict(int)
    for opp in closed_opps:
        acc_id = opp["node"]["Account"]["Id"]
        close_date = datetime.strptime(opp["node"]["CloseDate"]["value"], '%Y-%m-%d')
        days_since_close = (datetime.now() - close_date).days

        if days_since_close <= 365:
            scores[acc_id] += 50
            closed_opps_count[acc_id] += 1
        else:
            scores[acc_id] += 30

    # Extra points for multiple closed won opportunities
    for acc_id, count in closed_opps_count.items():
        if count > 1:
            scores[acc_id] += 25

    # Scoring for interactions
    for account in all_accounts:
        interactions = Interaction.query.filter_by(account_id=account.Id).all()
        if scores[account.Id] is None and interactions is None:
            scores[account.Id] = 0
        for interaction in interactions:
            scores[account.Id] += 5
            if interaction.interaction_type == InteractionType.meeting:
                scores[account.Id] += 10



    # Scoring for open opportunities in the next 6 months
    for opp in open_opps:
        if opp["node"]["Account"] is not None:
            acc_id = opp["node"]["Account"]["Id"]
            close_date = datetime.strptime(opp["node"]["CloseDate"]["value"], '%Y-%m-%d')
            days_until_close = (close_date - datetime.now()).days
            if 180 >= days_until_close > 0:
                scores[acc_id] += 20
            elif days_until_close < 0:
                scores[acc_id] += 12

    # # Ensure no score exceeds 99
    # for acc_id in scores:
    #     scores[acc_id] = min(scores[acc_id], 99)

    # Determine cluster boundaries dynamically using percentiles
    sorted_scores_only = sorted(scores.values(), reverse=True)
    first_boundary = sorted_scores_only[int(0.10 * len(sorted_scores_only))]
    second_boundary = sorted_scores_only[int(0.25 * len(sorted_scores_only))]
    third_boundary = sorted_scores_only[int(0.55 * len(sorted_scores_only))]

    # Group companies into ranks based on score clusters
    ranked_scores = {}
    # for acc_id, score in scores.items():
    #     if score >= first_boundary:
    #         rank = 1
    #     elif score >= second_boundary:
    #         rank = 2
    #     elif score >= third_boundary:
    #         rank = 3
    #     else:
    #         rank = 4
    #     ranked_scores[acc_id] = (score, rank)

    # get the max score from scores, then normalize all with the max score being a 99
    max_score = max(scores.values())
    for acc_id, score in scores.items():
    #     normalize the scores for each score 0-99 and then round to nearest int
        normalized_score = int(round((score/max_score)*99))
        ranked_scores[acc_id] = (normalized_score, 1)

    return ranked_scores


