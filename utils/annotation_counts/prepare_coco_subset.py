# SPDX-License-Identifier: MIT

"""
Cut COCO 2017 val down to the first N images (sorted by file name) so the task
can be rebuilt the same way on any machine.

Writes into the output directory:
  instances_subset.json  annotations for those images only, to import as COCO 1.0
  labels.json            the 80 COCO categories in CVAT's label format
  images.txt             paths of the selected images, one per line
  expected_counts.json   per-class counts straight from the JSON: COCO objects, and
                         the shapes CVAT creates from them on import, which is what
                         the endpoint counts
"""

import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("annotations", type=Path, help="path to instances_val2017.json")
    parser.add_argument("images_dir", type=Path, help="path to the val2017 image folder")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--count", type=int, default=1000, help="number of images to keep")
    args = parser.parse_args()

    coco = json.loads(args.annotations.read_text())
    images = sorted(coco["images"], key=lambda image: image["file_name"])[: args.count]
    image_ids = {image["id"] for image in images}
    annotations = [ann for ann in coco["annotations"] if ann["image_id"] in image_ids]
    categories = coco["categories"]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    subset = {**coco, "images": images, "annotations": annotations}
    (args.output_dir / "instances_subset.json").write_text(json.dumps(subset))
    (args.output_dir / "labels.json").write_text(
        json.dumps([{"name": category["name"], "attributes": []} for category in categories])
    )
    (args.output_dir / "images.txt").write_text(
        "\n".join(str(args.images_dir / image["file_name"]) for image in images) + "\n"
    )

    names = {category["id"]: category["name"] for category in categories}
    objects = Counter()
    shapes = Counter()
    for ann in annotations:
        name = names[ann["category_id"]]
        objects[name] += 1
        # CVAT's COCO import turns every part of a polygon segmentation into its own
        # polygon shape, and a crowd region (RLE) into one mask.
        shapes[name] += 1 if ann["iscrowd"] else len(ann["segmentation"])

    expected = {
        "images": len(images),
        "annotations": len(annotations),
        "crowd_annotations": sum(ann["iscrowd"] for ann in annotations),
        "shapes": shapes.total(),
        "per_class_objects": dict(objects.most_common()),
        "per_class_shapes": dict(shapes.most_common()),
    }
    (args.output_dir / "expected_counts.json").write_text(json.dumps(expected, indent=2))

    print(
        f"{len(images)} images, {len(annotations)} annotations, {shapes.total()} shapes in CVAT,"
        f" {len(objects)} classes in use"
    )


if __name__ == "__main__":
    main()
