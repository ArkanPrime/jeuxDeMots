import requests
import argparse

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

# Charger les relations disponibles
relations_dict = get_relation_types()

def get_r_isa_nodes(node_a):
    """Récupère les noms des nœuds ayant une relation 'r_isa' avec nodeA, triés par poids décroissant, en supprimant ceux avec un poids négatif."""
    
    r_isa_id = relations_dict.get("r_isa", {}).get("id")
    if r_isa_id is None:
        print("Erreur : relation 'r_isa' non trouvée.")
        return []

    url = f"{BASE_URL}/relations/from/{node_a}"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Erreur lors de la requête pour {node_a}")
        return []

    data = response.json()
    nodes = {node["id"]: node["name"] for node in data.get("nodes", [])}
    relations = data.get("relations", [])

    isa_nodes = [
        (nodes[rel["node2"]], rel["w"]) 
        for rel in relations if rel["type"] == r_isa_id and rel["node2"] in nodes and rel["w"] > 0
    ]
    
    return sorted(isa_nodes, key=lambda x: x[1], reverse=True)

def check_relation_from_to(node1, relation, node2):
    relation_info = relations_dict.get(relation)
    if not relation_info:
        return None
    
    relation_id = relation_info["id"]
    url = f"{BASE_URL}/relations/from/{node1}/to/{node2}"
    response = requests.get(url)
    
    if response.status_code != 200:
        return None
    
    data = response.json()
    relations = data.get("relations", [])
    
    for rel in relations:
        if rel["type"] == relation_id:
            return rel["w"]
    
    return None

def normalize_weight(weight, min_weight, max_weight):
    """Normalise un poids entre 0 et 1."""
    if max_weight == min_weight:
        return 0.5  # Éviter la division par zéro
    return (weight - min_weight) / (max_weight - min_weight)

def deduction(node_a, relation, node_b):
    list_isa = get_r_isa_nodes(node_a)
    if not list_isa:
        return
    
    max_isa_weight = max([w for _, w in list_isa], default=1)
    min_isa_weight = min([w for _, w in list_isa], default=0)
    
    matching_relations = []
    for name, isa_weight in list_isa:
        rel_weight = check_relation_from_to(name, relation, node_b)
        if rel_weight is not None:
            max_rel_weight = max(rel_weight, 1)
            min_rel_weight = min(rel_weight, 0)
            
            norm_isa_weight = normalize_weight(isa_weight, min_isa_weight, max_isa_weight)
            norm_rel_weight = normalize_weight(rel_weight, min_rel_weight, max_rel_weight)
            final_score = (norm_isa_weight + norm_rel_weight) / 2
            
            matching_relations.append((name, node_b, relation, isa_weight, rel_weight, final_score))
    
    sorted_results = sorted(matching_relations, key=lambda x: x[5], reverse=True)
    
    for idx, (name, node_b, relation, isa_weight, rel_weight, score) in enumerate(sorted_results, start=1):
        print(f"{idx} | oui | {name} {relation} {node_b} | ISA Weight: {isa_weight:.2f} | Relation Weight: {rel_weight:.2f} | Score: {score:.2f}")

if __name__ == "__main__":
    while True:
        nodeA = input("Entrez le premier nœud (ou 'exit' pour quitter) : ")
        if nodeA.lower() == 'exit':
            break
        relation = input("Entrez la relation (name ou gpname) : ")
        nodeB = input("Entrez le deuxième nœud : ")
        deduction(nodeA, relation, nodeB)
