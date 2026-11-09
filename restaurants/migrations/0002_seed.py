from django.db import migrations

# (slug, name, category, extra tags, Google place ID)
PLACES = [
    ('5forty-cafe', '5Forty Café', 'cafe', 'breakfast lunch dinner apres', 'ChIJnSD7ZJyyf1MRUjU8aLfVmj0'),
    ('annex-food-drink', 'Annex Food + Drink', 'family', 'breakfast lunch', 'ChIJkV8o6Jqyf1MRzz6pyYeLMx8'),
    ('baby-dohs-mountain-fair', "Baby Doh's Mountain Fair", 'treats', 'treats', 'ChIJiTT1Tx2zf1MR6i5Ug4cF5kw'),
    ('bolacco-cafe', 'Bolacco Café', 'cafe', 'coffee breakfast lunch', 'ChIJuZe7B5uyf1MRi9HqvIqR618'),
    ('bottoms-bar-grill', 'Bottoms Bar & Grill', 'pub', 'apres dinner', 'ChIJuZe7B5uyf1MRnL--HDXUl6g'),
    ('cafe-soleil', 'Café Soleil', 'cafe', 'coffee breakfast', 'ChIJhYRUgZyyf1MR6re3md3tg_0'),
    ('cahilty-creek-kitchen-taproom', 'Cahilty Creek Kitchen & Taproom', 'pub', 'apres dinner', 'ChIJjQTGSpyyf1MRHr1VHTg1G3c'),
    ('capones-italian-kitchen', 'Capones Italian Kitchen', 'italian', 'dinner', 'ChIJNw_ihAWzf1MRjs4u51FYRVM'),
    ('chez-joe-poutine', 'Chez Joe Poutine', 'burger', 'lunch', 'ChIJVQ3knZuyf1MRKff8GHjKBs0'),
    ('fondue-stube', 'Fondue Stube', 'fondue', 'dinner', ''),
    ('grand-mornings', 'Grand Mornings', 'cafe', 'breakfast', 'ChIJb1EYq8mzf1MRrGJxwPz6Sdk'),
    ('mantles-restaurant-lounge', 'Mantles Restaurant & Lounge', 'fine', 'breakfast dinner', 'ChIJ3_dg7JKyf1MRQxd6vsQM4Jc'),
    ('masas-bar-grill', "Masa's Bar & Grill", 'pub', 'apres lunch dinner', 'ChIJhYRUgZyyf1MRNm4x52tSSw4'),
    ('morriseys-public-house', "Morrisey's Public House", 'pub', 'apres dinner', 'ChIJW1hg7JKyf1MRIVF-3SU0sLw'),
    ('mountain-high-pizza', 'Mountain High Pizza', 'pizza', 'lunch dinner', 'ChIJh6TaB5uyf1MRzNKxQHlPa3Y'),
    ('oya-japanese-cuisine-sun-peaks', 'Oya Japanese Cuisine', 'japanese', 'dinner', 'ChIJh0GHewuzf1MRZpzFFuhiFgE'),
    ('powder-hounds', 'Powder Hounds', 'german', 'dinner', 'ChIJf_dLCJuyf1MRPCALtPFa_W4'),
    ('steakhouse-at-sun-peaks-lodge', 'Steakhouse at Sun Peaks Lodge', 'fine', 'dinner', ''),
    ('sunburst-bar-eatery', 'Sunburst Bar & Eatery', 'family', 'lunch apres', 'ChIJA-NY4pqyf1MRweDjGjmA6PE'),
    ('tod-mountain-cafe', 'Tod Mountain Café', 'cafe', 'coffee breakfast', 'ChIJh6TaB5uyf1MRGucE0WP-vFw'),
    ('umbrella-cafe', 'Umbrella Café', 'cafe', 'coffee breakfast', 'ChIJt66hF56yf1MRJ9DncIwEGVU'),
    ('vertical-cafe', 'Vertical Café & Bistro', 'cafe', 'coffee breakfast lunch', 'ChIJuZe7B5uyf1MR3jGz-XyAwkk'),
    ('magic-cattle-guard', 'Magic Cattle Guard Diner', 'burger', 'lunch dinner', 'ChIJH2gFSeSzf1MRpa8-sdMlKTI'),
]


def seed(apps, schema_editor):
    Restaurant = apps.get_model("restaurants", "Restaurant")
    for slug, name, category, tags, place_id in PLACES:
        Restaurant.objects.get_or_create(
            slug=slug, defaults={"name": name, "category": category, "tags": tags, "place_id": place_id})


class Migration(migrations.Migration):
    dependencies = [("restaurants", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
