import requests
import concurrent.futures
import math
from functools import lru_cache

BASE_URL = "https://jdm-api.demo.lirmm.fr/v0"

def get_relation_types():
    url = f"{BASE_URL}/relations_types"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
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
    response_final = requests.get(url_final)
    if response_final.status_code == 200:
        data_final = response_final.json()
        relations_final = data_final.get("relations", [])
        if relations_final:
            return relations_final[0].get("w", 0)
    return None

def deductive_inference(node_a, second_relation, node_b):
    min_weight = 1
    """
    Réalise l'inférence en deux étapes.
    La première relation (node_a -> intermédiaire) est toujours considérée comme "r_isa".
    Pour chaque nœud intermédiaire, on récupère le poids de la relation de type second_relation (par ex "r_agent-1")
    entre ce nœud et node_b.
    
    Le score est calculé via la moyenne harmonique :
         score = 2 * (n1 * n2) / (n1 + n2)
    
    Le résultat final est formaté sous la forme :
       node_a, "r_isa", nœud intermédiaire, second_relation, node_b, score
    """
    # 1. Récupérer les relations de type 6 depuis node_a, avec un filtre sur le poids minimal
    url = f"{BASE_URL}/relations/from/{node_a}?types_ids=6&min_weight={min_weight}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Erreur: Requête échouée pour {node_a} (Statut {response.status_code})")
        return {}
    data = response.json()
    
    # Construire un dictionnaire ID → nom à partir du champ "nodes"
    nodes_dict = {node["id"]: node["name"] for node in data.get("nodes", [])}

    # Liste 1 : pour chaque relation, conserver le nœud intermédiaire et son poids,
    # avec la première relation fixée à "r_isa"
    first_list = []
    for rel in data.get("relations", []):
        node_id = rel.get("node2")
        intermediate = nodes_dict.get(node_id, "Nom inconnu")
        weight = rel.get("w", 0)
        first_list.append({
            "intermediate": intermediate,
            "weight": weight,
            "first_relation": "r_isa"  # Fixe la première relation à "r_isa"
        })
    
    # Trier par ordre décroissant sur le poids de la première relation
    first_list = sorted(first_list, key=lambda x: x["weight"], reverse=True)
    
    # Normalisation des poids pour la première relation
    if first_list:
        min_w = min(item["weight"] for item in first_list)
        max_w = max(item["weight"] for item in first_list)
        diff = max_w - min_w
        for item in first_list:
            item["normalized_weight"] = (item["weight"] - min_w) / diff if diff else 1.0
    
    # 2. Récupérer l'ID de la relation finale pour la deuxième relation
    relations_dict = get_relation_types()
    second_relation_obj = relations_dict.get(second_relation)
    if not second_relation_obj:
        print(f"Erreur: Relation '{second_relation}' non trouvée.")
        return {}
    second_relation_id = second_relation_obj.get("id")
    if second_relation_id is None:
        print(f"Erreur: ID non trouvé pour la relation '{second_relation}'")
        return {}
    
    # 3. Pour chaque nœud intermédiaire de first_list, récupérer en parallèle le poids de la relation finale
    second_list = first_list.copy()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_item = {
            executor.submit(get_final_relation_weight, item["intermediate"], node_b, second_relation_id): item
            for item in second_list
        }
        for future in concurrent.futures.as_completed(future_to_item):
            item = future_to_item[future]
            try:
                final_weight = future.result()
                item["final_relation_weight"] = final_weight
            except Exception:
                item["final_relation_weight"] = None
    
    # Filtrer pour ne garder que les nœuds ayant une relation finale
    second_list = [item for item in second_list if item.get("final_relation_weight") is not None]
    
    # Normalisation des poids pour la deuxième relation
    if second_list:
        min_final = min(item["final_relation_weight"] for item in second_list)
        max_final = max(item["final_relation_weight"] for item in second_list)
        diff_final = max_final - min_final
        for item in second_list:
            item["normalized_final_weight"] = (item["final_relation_weight"] - min_final) / diff_final if diff_final else 1.0
        second_list = sorted(second_list, key=lambda x: x["final_relation_weight"], reverse=True)
    
    # 4. Calculer le score via la moyenne harmonique :
    #    score = 2 * (n1 * n2) / (n1 + n2)
    final_list = []
    for item in second_list:
        n1 = item["normalized_weight"]
        n2 = item["normalized_final_weight"]
        score = 2 * (n1 * n2) / (n1 + n2) if (n1 + n2) > 0 else 0
        final_list.append({
            "node_a": node_a,
            "first_relation": "r_isa",  # toujours "r_isa"
            "intermediate_node": item["intermediate"],
            "second_relation": second_relation,
            "node_b": node_b,
            "score": score,
            
        })
    
    # Trier la liste finale par score décroissant
    final_list = sorted(final_list, key=lambda x: x["score"], reverse=True)
    return final_list

# Exemple d'utilisation
# results = deductive_inference("kiwi", "r_agent-1", "voler")

# Format d'affichage final
# print("=== Résultats Formatés ===")
# for i, res in enumerate(results, 1):
#     # Format : "1 | tigre r_isa <intermédiaire> & <intermédiaire> r_agent-1 chasser | score"
#     formatted = f"{res['node_a']} r_isa {res['intermediate_node']} & {res['intermediate_node']} {res['second_relation']} {res['node_b']}"
#     print(f"{i} | {formatted} | {res['score']:.2f}")
