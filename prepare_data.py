import pandas as pd
import random
import os


def prepare_dataset(csv_path, brand_author_id="AppleSupport", sample_size=250):
    print(f"Loading {csv_path} (this might take a minute, it's 500MB)...")
    df = pd.read_csv(csv_path)

    print(f"Total tweets in dataset: {len(df)}")

    df["tweet_id_str"] = df["tweet_id"].astype(str).str.replace(r"\.0$", "", regex=True)
    df["in_response_to_tweet_id_str"] = (
        df["in_response_to_tweet_id"].astype(str).str.replace(r"\.0$", "", regex=True)
    )

    # 1. Find all outbound tweets by the brand
    brand_replies = df[(df["author_id"] == brand_author_id) & (df["inbound"] == False)]
    print(f"Total outbound replies by {brand_author_id}: {len(brand_replies)}")

    # 2. Get the tweet IDs they were responding to
    in_response_ids = brand_replies["in_response_to_tweet_id_str"].dropna().tolist()

    # 3. Find the original customer inbound tweets
    customer_inbounds = df[df["tweet_id_str"].isin(in_response_ids)]
    print(f"Found {len(customer_inbounds)} original customer tweets.")

    # 4. Join them together into a pair: Customer Message -> Brand Response
    customer_inbounds_renamed = customer_inbounds.rename(
        columns={
            "tweet_id_str": "customer_tweet_id",
            "text": "customer_text",
            "author_id": "customer_author_id",
        }
    )[["customer_tweet_id", "customer_text", "customer_author_id"]]

    brand_replies_renamed = brand_replies.rename(
        columns={
            "in_response_to_tweet_id_str": "customer_tweet_id",
            "text": "brand_response_text",
        }
    )

    merged = pd.merge(
        customer_inbounds_renamed,
        brand_replies_renamed,
        on="customer_tweet_id",
        how="inner",
    )

    print(f"Successfully reconstructed {len(merged)} conversation pairs.")

    # 5. Sample for the Golden Set
    merged = merged.drop_duplicates(subset=["customer_text"])

    sample_size = min(sample_size, len(merged))
    golden_set = merged.sample(n=sample_size, random_state=42).copy()

    # Add blank columns for our hand-labelling
    golden_set["intent_label"] = ""
    golden_set["action_label"] = ""  # 'auto' or 'escalate'

    # Clean up customer text (remove the @AppleSupport mention if it's there to make it cleaner)
    golden_set["customer_text"] = golden_set["customer_text"].str.replace(
        f"@{brand_author_id} ", "", case=False
    )

    out_path = "data/apple_support_golden_set.csv"
    golden_set.to_csv(out_path, index=False)

    print(f"Saved {sample_size} examples to {out_path} for hand-labelling.")
    print("\nSample row:")
    print(f"Customer: {golden_set.iloc[0]['customer_text']}")
    print(f"Brand: {golden_set.iloc[0]['brand_response_text']}")


if __name__ == "__main__":
    prepare_dataset("data/twcs.csv", brand_author_id="AppleSupport", sample_size=200)
