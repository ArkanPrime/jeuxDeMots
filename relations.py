import requests
import json

def load_relation_types(file_path):
    """Charge les types de relations depuis un fichier JSON et crée une correspondance entre noms, gpnames et IDs."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            relation_data = json.load(file)
            return {rel["name"]: rel["id"] for rel in relation_data}, {rel["gpname"]: rel["id"] for rel in relation_data}
    except Exception as e:
        print(f"Erreur: Impossible de charger les types de relations ({e})")
        return {}, {}

def isRelationDirect(nodeA, relation, nodeB, relation_map, gpname_map):
    """Vérifie si la relation entrée correspond à une relation existante entre nodeA et nodeB."""
    url = f"https://jdm-api.demo.lirmm.fr/v0/relations/from/{nodeA}/to/{nodeB}"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Erreur: Impossible d'obtenir les relations ({response.status_code})")
        return
    
    data = response.json()
    relations = data.get("relations", [])
    
    if not relations:
        print(f"Aucune relation trouvée entre {nodeA} et {nodeB}.")
        return

    # Vérifier si la relation entrée correspond à un ID numérique
    relation_id = relation_map.get(relation) or gpname_map.get(relation)
    if relation_id is None:
        print(f"Relation '{relation}' inconnue dans types_relations.json.")
        return
    
    # Vérification des relations trouvées
    found = False
    for rel in sorted(relations, key=lambda r: r["w"], reverse=True):
        if rel["type"] == relation_id:
            print(f"✅ {nodeA} {relation} {nodeB} | Poids: {rel['w']}")
            found = True
    
    if not found:
        print(f"❌ Aucune relation '{relation}' trouvée entre {nodeA} et {nodeB}.")

def isRelationSuperior(nodeA, relation, nodeB, relation_map, gpname_map):
    """Recherche toutes les instances où A est un C, et C a la relation demandée avec B."""
    url = f"https://jdm-api.demo.lirmm.fr/v0/relations/from/{nodeA}"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Erreur: Impossible d'obtenir les relations de {nodeA} ({response.status_code})")
        return
    
    data = response.json()
    relations = data.get("relations", [])
    nodes = {node["id"]: node["name"] for node in data.get("nodes", [])}  # Créer un mapping ID -> Nom
    
    if not relations:
        print(f"Aucune relation trouvée pour {nodeA}.")
        return

    relation_isa_id = relation_map.get("r_isa") or gpname_map.get("r_isa")
    if relation_isa_id is None:
        print("Relation 'r_isa' inconnue dans types_relations.json.")
        return
    
    # Filtrer et afficher uniquement les relations de type r_isa avec leurs noms
    isa_relations = [rel for rel in relations if rel["type"] == relation_isa_id]
    
    if not isa_relations:
        print(f"Aucune relation 'r_isa' trouvée pour {nodeA}.")
        return
    
    for rel in isa_relations:
        node_name = nodes.get(rel['node2'], f"ID-{rel['node2']}")  # Récupérer le nom directement depuis la réponse
        print(f"🔎 {nodeA} r_isa {node_name} | Poids: {rel['w']}")
        isRelationDirect(node_name, relation, nodeB, relation_map, gpname_map)  # Appliquer isRelationDirect

def main():
    relation_types, gpname_types = load_relation_types("types_relations.json")  # Charge la correspondance 'r_syn' -> 5

    while True:
        user_input = input("Entrez une requête sous la forme 'mot1 relation mot2' (ou 'q' pour quitter) : ")
        if user_input.lower() == 'q':
            break
        
        parts = user_input.strip().split()
        if len(parts) != 3:
            print("Erreur: veuillez entrer une requête sous la forme 'mot1 relation mot2'.")
            continue
        
        node1, relation, node2 = parts[0], parts[1], parts[2]
        isRelationDirect(node1, relation, node2, relation_types, gpname_types)
        isRelationSuperior(node1, relation, node2, relation_types, gpname_types)

if __name__ == "__main__":
    main()
