import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

from tplinkrouterc6u import TplinkRouterProvider

router = TplinkRouterProvider.get_client(
    os.environ["ROUTER_HOST"], os.environ["ROUTER_PASSWORD"], username=os.environ["ROUTER_USERNAME"]
)
router.authorize()
try:
    for form in ["guest", "all"]:
        try:
            data = router.request(f"admin/wireless?form={form}", "operation=read")
            print(f"--- form={form} ---")
            for k, v in data.items():
                if "guest" in k.lower() or "isolat" in k.lower() or "iot" in k.lower():
                    print(f"  {k} = {v}")
        except Exception as e:
            print(f"form={form} failed: {e}")
finally:
    router.logout()
