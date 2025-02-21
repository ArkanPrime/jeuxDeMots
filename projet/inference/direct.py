import requests
from functools import lru_cache

# URL de base de l'API
BASE_URL = "https://jdm-api.demo.lirmm.fr/v0"

# Charger les types de relations
def get_relation_types():
    """Récupère et stocke tous les types de relations disponibles."""
    url = f"{BASE_URL}/relations_types"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        relations_dict = {rel["id"]: rel for rel in data}  # Associer ID → Infos
        relations_dict.update({rel["name"]: rel for rel in data})  # Associer Name → Infos
        relations_dict.update({rel["gpname"]: rel for rel in data})  # Associer Gpname → Infos
        return relations_dict
    else:
        print("Erreur lors de la récupération des types de relations.")
        return {}
    
def direct_inference(node_a, relation, node_b): # on veut la relation sous forme name ou gpname
    relations_dict = get_relation_types()
    relation_info = relations_dict.get(relation)
    
    if not relation_info:
        print(f"Erreur: Relation '{relation}' non trouvée.")
        return []
    
    relation_id = relation_info.get("id")
    if relation_id is None:
        print(f"Erreur: ID non trouvé pour la relation '{relation}'")
        return []
    
    url = f"{BASE_URL}/relations/from/{node_a}/to/{node_b}?types_ids={relation_id}"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Erreur: Requête échouée pour {node_a} {relation} {node_b} (Statut {response.status_code})")
        return []
    
    data = response.json()
    relations = data.get("relations", [])
    results = []
    
    # ici on a juste les relations du bon type, on les ajoute à la liste des résultats avec juste le nom et poids
    for rel in relations:
        results.append((node_a, rel.get("w", 0)))
    
    print(results)
    return results
