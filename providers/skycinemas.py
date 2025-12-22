from providers.fusionintel import FusionIntelProvider


class SkyCinemasProvider(FusionIntelProvider):
    cinema_name = "Sky Cinemas"
    location = "Sangotedo, Lagos"
    token_env_var = "SKY_CINEMAS_TOKEN"
