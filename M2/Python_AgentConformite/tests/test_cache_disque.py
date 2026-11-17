"""Tests du cache disque : la fonction d'appel est un faux, AUCUN appel API."""

from src import cache_disque as cd

ARGS = dict(modele="claude-sonnet-5-5", systeme="consignes + doc", messages=[{"role": "user", "content": "s1"}])


def test_cle_stable_et_sensible_a_la_version():
    a = cd.cle_cache(**ARGS, version_prompt="v1")
    assert a == cd.cle_cache(**ARGS, version_prompt="v1")
    assert a != cd.cle_cache(**ARGS, version_prompt="v2")


def test_cle_independante_de_l_ordre_des_parametres():
    a = cd.cle_cache(**ARGS, version_prompt="v1", params={"max_tokens": 8000, "effort": "medium"})
    b = cd.cle_cache(**ARGS, version_prompt="v1", params={"effort": "medium", "max_tokens": 8000})
    assert a == b


def test_appel_memoise_n_appelle_qu_une_fois(tmp_path):
    compteur = {"n": 0}

    def faux_appel(**kwargs):
        compteur["n"] += 1
        return {"contenu": "réponse", "usage": {"output_tokens": 12}}

    r1, cache1 = cd.appel_memoise(faux_appel, **ARGS, version_prompt="v1", dossier=tmp_path)
    r2, cache2 = cd.appel_memoise(faux_appel, **ARGS, version_prompt="v1", dossier=tmp_path)
    assert (cache1, cache2) == (False, True)
    assert r1 == r2
    assert compteur["n"] == 1

    # une nouvelle version du prompt déclenche un nouvel appel
    cd.appel_memoise(faux_appel, **ARGS, version_prompt="v2", dossier=tmp_path)
    assert compteur["n"] == 2
