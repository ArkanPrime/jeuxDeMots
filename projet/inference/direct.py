import requests
from functools import lru_cache

BASE_URL = "https://jdm-api.demo.lirmm.fr/v0"
session = requests.Session()  # Réutilise les connexions HTTP

@lru_cache(maxsize=32)
def get_relation_types():
    """Récupère et met en cache tous les types de relations disponibles."""
    url = f"{BASE_URL}/relations_types"
    response = session.get(url)
    if response.status_code == 200:
        data = response.json()
        relations_dict = {rel["id"]: rel for rel in data}      # Index par ID
        relations_dict.update({rel["name"]: rel for rel in data})  # Index par nom
        relations_dict.update({rel["gpname"]: rel for rel in data})  # Index par gpname
        return relations_dict
    else:
        print("Erreur lors de la récupération des types de relations.")
        return {}

def direct_inference(node_a, relation, node_b):
    """
    Effectue une inférence directe entre node_a et node_b pour un type de relation donné
    (identifié par son name ou gpname) et retourne une liste de tuples (node_a, poids).
    """
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
    response = session.get(url)
    
    if response.status_code != 200:
        return []
    
    data = response.json()
    relations = data.get("relations", [])
    results = [(node_a, rel.get("w", 0)) for rel in relations]
    
    print(results)
    return results

# Exemple d'utilisation :
# direct_inference("kiwi", "r_agent-1", "voler")
