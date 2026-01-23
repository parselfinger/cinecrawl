from providers.fusionintel import FusionIntelProvider


class EbonyLifeProvider(FusionIntelProvider):
    cinema_name = "EbonyLife Cinemas"
    location = "Victoria Island, Lagos"
    token_env_var = "EBONY_LIFE_TOKEN"
    base_movie_url = "https://www.ebonylifecinemas.com/movies/"
