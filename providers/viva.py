from providers.fusionintel import FusionIntelProvider


class VivaIkejaProvider(FusionIntelProvider):
    cinema_name = "Viva Cinemas"
    location = "Ikeja, Lagos"
    token_env_var = "VIVA_CINEMAS_TOKEN"
    cinema_id = "viv-27fd41dc"


class VivaLekkiProvider(FusionIntelProvider):
    cinema_name = "Viva Cinemas"
    location = "Lekki, Lagos"
    token_env_var = "VIVA_CINEMAS_TOKEN"
    cinema_id = "viv-6ac91519"
