import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

from tplinkrouterc6u import TplinkRouterProvider

router = TplinkRouterProvider.get_client(
    os.environ["ROUTER_HOST"], os.environ["ROUTER_PASSWORD"], username=os.environ["ROUTER_USERNAME"]
)
router.authorize()
print("client class:", type(router).__name__)
try:
    data = router.request("admin/wireless?form=all&operation=read", "operation=read")
    print("--- form=all&operation=read (GET style, full dump of guest/iot/isolat keys) ---")
    for k, v in sorted(data.items()):
        if "guest" in k.lower() or "isolat" in k.lower() or "iot" in k.lower() or "ssid" in k.lower():
            print(f"  {k} = {v}")
finally:
    router.logout()
