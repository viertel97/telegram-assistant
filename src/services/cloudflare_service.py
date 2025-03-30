import requests
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging
from telegram import Update
from telegram.ext import CallbackContext

from src.services.logging_service import log_to_telegram

logger = setup_logging(__file__)
CLOUDFLARE_API_KEY, CLOUDFLARE_ZONE_ID, PRIVATE_IP, HOSTED_ID = get_secrets(
	[
		"cloudflare/api_key",
		"cloudflare/zone_id",
		"cloudflare/private_ip",
		"cloudflare/hosted_ip",
	],
)

HEADERS = {
	"Content-Type": "application/json",
	"Authorization": "Bearer " + CLOUDFLARE_API_KEY,
}


def get_current_dns_entries():
	r = requests.get(
		f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records",
		headers=HEADERS,
	)
	result = r.json()
	return result["result"]


async def toggle_ips(update: Update, context: CallbackContext):
	current_dns_entries = get_current_dns_entries()

	if HOSTED_ID in str(current_dns_entries) and PRIVATE_IP not in str(current_dns_entries):
		await log_to_telegram("switch from non_private_ip to private_ip", logger, update)
		selected_ip = PRIVATE_IP
		proxied = False
	else:
		await log_to_telegram("switch from private_ip to non_private_ip", logger, update)
		selected_ip = HOSTED_ID
		proxied = False

	for dns_entry in current_dns_entries:
		temp = requests.put(
			f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records/{dns_entry['id']}",
			headers=HEADERS,
			json={
				"name": dns_entry["name"],
				"type": dns_entry["type"],
				"content": selected_ip,
				"ttl": 1,
				"proxied": proxied,
			},
		)
		if temp.status_code != 200:
			await log_to_telegram(f"error while switching ips: {temp.json()}", logger, update)
		else:
			await log_to_telegram(f"switched ips: {temp.json()}", logger, update)
