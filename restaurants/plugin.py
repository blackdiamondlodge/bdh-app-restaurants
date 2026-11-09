from bdh_sdk import PluginSpec, Tile

spec = PluginSpec(
    id="restaurants",
    app="restaurants",
    urls="restaurants.urls",
    status="restaurants.homepage.status",
    tiles=(
        Tile(
            title="Restaurants",
            url_name="restaurants",
            icon="restaurants/hub/icon.svg",
            section="mountain",
            subtitle="Where to eat in Sun Peaks",
            order=40,
        ),
    ),
)
