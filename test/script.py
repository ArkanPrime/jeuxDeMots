import requests
import argparse
import math
import time
import asyncio
import aiohttp
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

# Charger les relations disponibles
relations_dict = get_relation_types()

@lru_cache(maxsize=1000)
def check_direct_relation(node_a, relation, node_b):
    """Vérifie s'il existe une relation directe entre nodeA et nodeB avec cache."""
    relation_info = relations_dict.get(relation)
    if not relation_info:
        return None
    
    relation_id = relation_info["id"]
    url = f"{BASE_URL}/relations/from/{node_a}/to/{node_b}?types_ids={relation_id}"
    response = requests.get(url)
    
    if response.status_code != 200:
        return None
    
    data = response.json()
    relations = data.get("relations", [])
    
    for rel in relations:
        if rel["type"] == relation_id:
            return rel["w"]
    
    return None

async def fetch_relation(session, node_a, node_b, relation_id):
    """Effectue une requête asynchrone pour vérifier une relation."""
    url = f"{BASE_URL}/relations/from/{node_a}/to/{node_b}?types_ids={relation_id}"
    async with session.get(url) as response:
        if response.status == 200:
            data = await response.json()
            relations = data.get("relations", [])
            for rel in relations:
                if rel["type"] == relation_id:
                    return node_a, rel["w"]
    return node_a, None

async def check_direct_relations_async(nodes, relation, node_b):
    """Vérifie en parallèle s'il existe une relation directe entre une liste de nodes et nodeB."""
    relation_info = relations_dict.get(relation)
    if not relation_info:
        return {}

    relation_id = relation_info["id"]
    results = {}

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_relation(session, node, node_b, relation_id) for node in nodes]
        responses = await asyncio.gather(*tasks)

    for node, weight in responses:
        if weight is not None:
            results[node] = weight

    return results

def get_r_isa_nodes(node_a):
    """Récupère les noms des nœuds ayant une relation 'r_isa' avec nodeA."""
    
    r_isa_id = relations_dict.get("r_isa", {}).get("id")
    if r_isa_id is None:
        print("Erreur : relation 'r_isa' non trouvée.")
        return []

    url = f"{BASE_URL}/relations/from/{node_a}?types_ids={r_isa_id}"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Erreur lors de la requête pour {node_a}")
        return []

    data = response.json()
    nodes = {node["id"]: node["name"] for node in data.get("nodes", [])}
    relations = data.get("relations", [])

    isa_nodes = [
        (nodes[rel["node2"]], rel["w"]) 
        for rel in relations if rel["node2"] in nodes and rel["w"] > 0
    ]
    
    return sorted(isa_nodes, key=lambda x: x[1], reverse=True)

def normalize_weight(weight, min_weight, max_weight):
    """Normalise un poids entre 0 et 1."""
    if max_weight == min_weight:
        return 0.5  # Éviter la division par zéro
    return (weight - min_weight) / (max_weight - min_weight)

def deduction(node_a, relation, node_b):
    start_time = time.time()
    all_results = []
    
    # Vérifier la relation directe avec cache
    direct_weight = check_direct_relation(node_a, relation, node_b)
    if direct_weight is not None:
        inference_path = f"{node_a} {relation} {node_b}"
        all_results.append((node_a, node_b, relation, None, direct_weight, 1.0, inference_path))
    
    # Vérifier l'inférence r_isa
    list_isa = get_r_isa_nodes(node_a)
    if list_isa:
        matching_relations = asyncio.run(check_direct_relations_async([name for name, _ in list_isa], relation, node_b))
        isa_weights = [w for _, w in list_isa]
        rel_weights = list(matching_relations.values())
        
        min_isa, max_isa = min(isa_weights), max(isa_weights)
        min_rel, max_rel = min(rel_weights), max(rel_weights)
        
        for name, isa_weight in list_isa:
            if name in matching_relations:
                rel_weight = matching_relations[name]
                if isa_weight is None or rel_weight is None or isa_weight <= 0 or rel_weight <= 0:
                    continue
                norm_isa_weight = normalize_weight(isa_weight, min_isa, max_isa)
                norm_rel_weight = normalize_weight(rel_weight, min_rel, max_rel)
                final_score = math.sqrt(norm_isa_weight * norm_rel_weight)
                inference_path = f"{node_a} r_isa {name} && {name} {relation} {node_b}"
                all_results.append((name, node_b, relation, isa_weight, rel_weight, final_score, inference_path))
    
    # Trier et afficher les 10 meilleurs résultats
    sorted_results = sorted(all_results, key=lambda x: x[5], reverse=True)[:10]
    
    for idx, (name, node_b, relation, isa_weight, rel_weight, score, inference_path) in enumerate(sorted_results, start=1):
        print(f"{idx} | oui | {inference_path} | Relation Weight: {rel_weight:.2f} | Score: {score:.2f}")
    
    end_time = time.time()
    print(f"Temps d'exécution : {end_time - start_time:.4f} secondes")


if __name__ == "__main__":
    while True:
        nodeA = input("Entrez le premier nœud (ou 'exit' pour quitter) : ")
        if nodeA.lower() == 'exit':
            break
        relation = input("Entrez la relation (name ou gpname) : ")
        nodeB = input("Entrez le deuxième nœud : ")
        deduction(nodeA, relation, nodeB)
