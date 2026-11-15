"""官方跨split精确重合的整文档隔离层；保留原暂定划分，不冻结新划分。"""


def quarantine_splits(rows, overlaps, observed_documents):
    by_doc = {row["document_id"]: row for row in rows}
    if len(by_doc) != len(rows) or not set(observed_documents) <= by_doc.keys():
        raise ValueError("duplicate/unknown document")
    clusters = {}
    for row in rows:
        if row["split"] not in {"train_fit", "train_dev", "train_confirm"}:
            raise ValueError("unexpected split")
        cluster = row["cluster_id"]
        if not cluster or (cluster in clusters and clusters[cluster] != row["split"]):
            raise ValueError("invalid or leaking existing cluster")
        clusters[cluster] = row["split"]
    excluded = set()
    for group in overlaps["tables"] + overlaps["documents"]:
        members = group["members"]
        splits = {member["official_split"] for member in members}
        if "train" in splits and splits & {"val", "test"}:
            excluded.update(m["document_id"] for m in members if m["official_split"] == "train")
    if not excluded <= by_doc.keys():
        raise ValueError("unknown overlap train document")
    excluded_clusters = {by_doc[doc]["cluster_id"] for doc in excluded}
    observed_clusters = {by_doc[doc]["cluster_id"] for doc in observed_documents}
    result = []
    for row in rows:
        if row["cluster_id"] in observed_clusters and row["split"] == "train_confirm":
            raise ValueError("observed document/cluster cannot remain unseen confirm")
        quarantine = row["cluster_id"] in excluded_clusters
        result.append(
            dict(
                row,
                effective_split="quarantine" if quarantine else row["split"],
                observed_cluster=row["cluster_id"] in observed_clusters,
                reason=(
                    "known_official_overlap"
                    if row["document_id"] in excluded
                    else "cluster_contains_known_official_overlap"
                )
                if quarantine
                else None,
                status="provisional_overlay_not_training_authorized",
            )
        )
    return result
