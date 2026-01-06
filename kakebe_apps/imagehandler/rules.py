IMAGE_RULES = {
    "listing": {
        "variants": {
            "thumb": {"max_size": 50_000},
            "medium": {"max_size": 200_000},
            "large": {"max_size": 350_000},
        },
        "min_images": 3,
    },
    "profile": {
        "variants": {
            "thumb": {"max_size": 50_000},
            "medium": {"max_size": 150_000},
        }
    },
    "store_banner": {
        "variants": {
            "large": {"max_size": 350_000},
        }
    },
}
