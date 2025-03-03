import requests
import concurrent.futures
from functools import lru_cache

BASE_URL = "https://jdm-api.demo.lirmm.fr/v0"
session = requests.Session()

@lru_cache(maxsize=32)
def get_relation_types():
    url = f"{BASE_URL}/relations_types"
    response = session.get(url)
    if response.status_code == 200:
        data = response.json()
        # Indexer par id, nom et gpname
        relations_dict = {rel["id"]: rel for rel in data}
        relations_dict.update({rel["name"]: rel for rel in data})
        relations_dict.update({rel["gpname"]: rel for rel in data})
        return relations_dict
    else:
        print("Erreur lors de la récupération des types de relations.")
        return {}

@lru_cache(maxsize=128)
def get_final_relation_weight(intermediary, node_b, relation_id):
    """
    Récupère le poids de la relation entre le nœud intermédiaire et node_b.
    Le résultat est mis en cache pour éviter les appels redondants.
    """
    url_final = f"{BASE_URL}/relations/from/{intermediary}/to/{node_b}?types_ids={relation_id}"
    response_final = session.get(url_final)
    if response_final.status_code == 200:
        data_final = response_final.json()
        relations_final = data_final.get("relations", [])
        if relations_final:
            return relations_final[0].get("w", 0)
    return None


def normalize_weights(items, weight_key, norm_key):
    if not items:
        return
    min_val = min(item[weight_key] for item in items)
    max_val = max(item[weight_key] for item in items)
    diff = max_val - min_val
    for item in items:
        item[norm_key] = (item[weight_key] - min_val) / diff if diff else 1.0


def inductive_inference(node_a, second_relation, node_b):
    min_weight = 1
    url = f"{BASE_URL}/relations/from/{node_a}?types_ids=8&min_weight={min_weight}"
    response = session.get(url)
    if response.status_code != 200:
        print(f"Erreur: Requête échouée pour {node_a} (Statut {response.status_code})")
        return {}
    data = response.json()
    nodes_dict = {node["id"]: node["name"] for node in data.get("nodes", [])}

    # 1. Construire la première liste avec la relation "r_hypo"
    first_list = [{
        "intermediate": nodes_dict.get(rel.get("node2"), "Nom inconnu"),
        "weight": rel.get("w", 0),
        "first_relation": "r_hypo"
    } for rel in data.get("relations", [])]
    normalize_weights(first_list, "weight", "normalized_weight")

    # 2. Récupérer l'ID de la relation finale pour second_relation
    relations_dict = get_relation_types()
    second_relation_obj = relations_dict.get(second_relation)
    if not second_relation_obj:
        print(f"Erreur: Relation '{second_relation}' non trouvée.")
        return {}
    second_relation_id = second_relation_obj.get("id")
    if second_relation_id is None:
        print(f"Erreur: ID non trouvé pour la relation '{second_relation}'")
        return {}

    # 3. Récupérer en parallèle le poids de la relation finale pour chaque nœud intermédiaire
    second_list = first_list.copy()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_item = {
            executor.submit(get_final_relation_weight, item["intermediate"], node_b, second_relation_id): item
            for item in second_list
        }
        for future in concurrent.futures.as_completed(future_to_item):
            item = future_to_item[future]
            try:
                item["final_relation_weight"] = future.result()
            except Exception:
                item["final_relation_weight"] = None
    second_list = [item for item in second_list if item.get("final_relation_weight") is not None]
    normalize_weights(second_list, "final_relation_weight", "normalized_final_weight")

    # 4. Calculer le score via la moyenne harmonique
    final_list = [{
        "node_a": node_a,
        "first_relation": "r_hypo",
        "intermediate_node": item["intermediate"],
        "second_relation": second_relation,
        "node_b": node_b,
        "score": 2 * (item["normalized_weight"] * item["normalized_final_weight"]) /
                 (item["normalized_weight"] + item["normalized_final_weight"]) if 
                 (item["normalized_weight"] + item["normalized_final_weight"]) > 0 else 0
    } for item in second_list]
    return final_list
