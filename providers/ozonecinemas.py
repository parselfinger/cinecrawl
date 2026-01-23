from providers.fusionintel import FusionIntelProvider


class OzoneCinemasProvider(FusionIntelProvider):
    cinema_name = "Ozone Cinemas"
    location = "Yaba, Lagos"
    token_env_var = "OZONE_CINEMAS_TOKEN"
    cinema_id = "ozo-a4239533"
    base_movie_url = "https://ozone.reachcinema.io/movies/"
