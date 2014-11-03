from ..models import NearWooCampaignDS


def camp_from_results_url(url):
    return models.NearWooCampaignDS.urlsafe_get(url.split('/')[-1])


