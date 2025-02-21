import sys

from inference.direct import direct_inference
from inference.deductive import deductive_inference
import time

def run_inference(node_a, relation, node_b):
    """Runs inference methods and retrieves raw data."""
    direct_results = direct_inference(node_a, relation, node_b)
    if direct_results[0][1] < 0:
        print("No.")
        return
    start_time = time.time()
    results = deductive_inference(node_a, relation, node_b)
    end_time = time.time()
    print(f"deductive time: {end_time - start_time:.2f} seconds")

    print("=== Affichage complet ===")
    for i, res in enumerate(results, 1):
        formatted = f"{res['node_a']} r_isa {res['intermediate_node']} & {res['intermediate_node']} {res['second_relation']} {res['node_b']}"
        print(f"{i} | {formatted} | {res['score']:.2f}")

    print("\n=== Top 10 ===")
    for i, res in enumerate(results[:10], 1):
        formatted = f"{res['node_a']} r_isa {res['intermediate_node']} & {res['intermediate_node']} {res['second_relation']} {res['node_b']}"
        print(f"{i} | {formatted} | {res['score']:.2f}")


if __name__ == "__main__":
    print("Enter queries in the format: nodeA relation nodeB")
    print("Type 'exit' to quit.")
    
    while True:
        user_input = input("→ ").strip()
        
        if user_input.lower() == 'exit':
            break
        
        parts = user_input.split()
        if len(parts) != 3:
            print("Invalid format. Use: nodeA relation nodeB")
            continue
        
        nodeA, relation, nodeB = parts
        run_inference(nodeA, relation, nodeB)