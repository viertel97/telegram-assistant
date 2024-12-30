import pandas as pd
from quarter_lib.logging import setup_logging

logger = setup_logging(__file__)


def create_mermaid_timeline(df):
	graph_str = "timeline"
	graph_str += "\n"
	graph_str += "\ttitle Obsidian Refresher\n"
	df["date_added"] = pd.to_datetime(df["date_added"])

	# Add a new column for date without minutes and seconds (only year, month, day, hour)
	df["hourly"] = df["date_added"].dt.floor("H")

	# Create a full range of hourly intervals between the min and max dates
	full_range = pd.date_range(start=df["hourly"].min(), end=df["hourly"].max(), freq="H")

	# Create a new DataFrame to ensure all hourly intervals are present
	df_full = pd.DataFrame(full_range, columns=["hourly"])

	# Merge the full range DataFrame with the original DataFrame
	df_merged = df_full.merge(df, on="hourly", how="left")

	# Fill missing values in 'content' with empty strings
	df_merged["content"] = df_merged["content"].fillna("")

	# Group by the 'hourly' column
	grouped = df_merged.groupby("hourly")

	for date_hour, group in grouped:
		graph_str += "\tsection " + str(date_hour.date()) + " " + str(date_hour.hour) + "\n".replace(":", ".")
		for index, row in group.iterrows():
			content = row["content"].replace("\n", " ").replace(":", ";")
			if pd.notnull(content) and content != "":
				date_added = (
					str(row["date_added"]).replace(":", ".")
					if "date_added" in row and pd.notnull(row["date_added"])
					else str(date_hour).replace(":", ".")
				)
				graph_str += f"\t\t{date_added} : {content}\n"

	logger.info("\n" + graph_str)
	return graph_str
