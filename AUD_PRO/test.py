import requests
import time

t0 = time.time()
for _ in range(5):
    hitting_time = time.time()
    requests.post("http://127.0.0.1:8000/parse", data={"text": "दस मिनट का टाइमर"})
print("Time:", time.time() - t0)

# import time
# from services.time_parser import parse_temporal

# t0 = time.time()
# for _ in range(100):
#     parse_temporal("दस मिनट का टाइमर")
# print("Direct call time:", time.time() - t0)