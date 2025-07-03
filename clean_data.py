
import pickle
import time
from itertools import islice

from hello3 import LMSResult

def main():
    filename = "scrape_url_cache.pkl"
    with open(filename, "rb") as f:
        data = pickle.load(f)

    # for k,v in islice(data.items(), 5):
    # for k,v in list(data.items())[-5:]:
    to_delete = []
    for k,v in data.items():
        # print(f"Key: {k}")
        # print("type(v.reasoning):", type(v.reasoning))
        if v.reasoning.startswith("(") or v.reasoning.startswith("No") or v.reasoning.startswith("URL"):
            to_delete.append(k)
            # if the reasoning is a tuple or list, convert it to a string
            #v.reasoning = str(v.reasoning)
        # if isinstance(v, LMSResult):
        #     print(f"Value: {v.model_dump(mode='json')}")
        # else:
        #     print(f"Value: {v}")
        # print()
    for k in to_delete:
        # print(f"Deleting key: {k}, Reasoning: {data[k].reasoning}")
        del data[k]

    with open(filename, "wb") as f:
        pickle.dump(data, f)
    

if __name__ == "__main__":
    main()