"""Une page scannée qui porte un petit texte (cachet « copie certifiée conforme ») doit être envoyée à l'OCR."""
from types import SimpleNamespace

from app.knowledge.extract import image_heavy


def _page(images, w=600.0, h=800.0):
    return SimpleNamespace(width=w, height=h, images=images)


def test_scan_with_stamp_text_is_image_heavy():
    page = _page([{"x0": 0, "x1": 600, "top": 0, "bottom": 800}])
    assert image_heavy(page, "PRESIDENCE DE LA REPUBLIQUE COPIE CERTIFIEE CONFORME " * 3)


def test_born_digital_page_with_small_logo_is_not():
    page = _page([{"x0": 10, "x1": 90, "top": 10, "bottom": 60}])
    assert not image_heavy(page, "Article 1. Texte court.")


def test_long_text_layer_is_never_ocred_even_with_background_image():
    page = _page([{"x0": 0, "x1": 600, "top": 0, "bottom": 800}])
    assert not image_heavy(page, "mot " * 400)


def test_broken_page_object_falls_back_silently():
    assert not image_heavy(SimpleNamespace(), "x" * 100)


def test_missing_articles_detects_gaps_without_inventing_numbers():
    from app.knowledge.ingest import missing_articles
    labels = [f"ARTICLE {n}" for n in range(1, 61) if n not in (52, 53, 58)] + [None, "TITRE V"]
    assert missing_articles(labels) == [52, 53, 58]
    assert missing_articles(["Article 1", "Article 2", "Article 4"]) == []  # trop peu d'articles : pas de conclusion
    assert missing_articles(["ARTICLE9", "ARTICLE 10", *[f"ARTICLE {n}" for n in range(11, 25)]]) == []


def test_very_sparse_numbering_is_not_reported_as_extraction_defect():
    from app.knowledge.ingest import missing_articles
    sparse = [f"Article {n}" for n in range(1, 200, 4)]  # loi modificative : numérotation lacunaire par nature
    assert missing_articles(sparse) == []


def test_text_between_section_heading_and_unrecognised_article_is_not_lost():
    """Régression : « TITRE V … ARTICLE §3 … » (OCR) supprimait tout le texte jusqu'au prochain article reconnu."""
    from app.knowledge.chunking import chunk_pages
    pages = [(1, "ARTICLE 1.- Premier article assez long pour exister dans le texte de la loi.\nARTICLE 2.- Deuxième article."),
             (2, "TITRE V\nDE L'AUTORITE DE PROTECTION\nARTICLE §3.- (1) L'Autorité est un organisme public indépendant chargé de veiller "
                 "à l'application de la présente loi et de délivrer les autorisations prévues par celle-ci, et de traiter les réclamations.\n"
                 "ARTICLE 4.- Quatrième article.")]
    drafts = chunk_pages(pages)
    assert any("organisme public indépendant" in d.text for d in drafts)


def test_parenthesised_article_numbers_of_uae_decrees_are_recognised():
    from app.knowledge.chunking import chunk_pages
    pages = [(1, "Article (1)\nDefinitions. Les termes suivants ont le sens indiqué ci-dessous pour l'application de ce décret-loi.\n"
                 "Article (2)\nChamp d'application. Ce décret-loi s'applique à toute entité établie dans l'État et à son personnel.")]
    arts = [d.article for d in chunk_pages(pages) if d.article]
    assert arts == ["Article (1)", "Article (2)"]
