import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
from tplinkrouterc6u import TplinkRouterProvider
router = TplinkRouterProvider.get_client(os.environ["ROUTER_HOST"], os.environ["ROUTER_PASSWORD"], username=os.environ["ROUTER_USERNAME"])
router.authorize()
status = router.get_status()
print("WAN IP:", status.wan_ipv4_addr)
router.logout()
