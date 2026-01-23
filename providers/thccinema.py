from providers.fusionintel import FusionIntelProvider


class THCCinemaProvider(FusionIntelProvider):
    cinema_name = "THC Cinema"
    location = "Agege, Lagos"
    token_env_var = "THC_CINEMA_TOKEN"
    base_movie_url = "https://cinemaxthc.ng/movies/"
