from flask_restful import current_app

from zou.app.models.project import Project
from zou.app.models.entity import Entity

from zou.app.services import assets_service, shots_service

from zou.app.blueprints.source.shotgun.base import (
    BaseImportShotgunResource,
    ImportRemoveShotgunBaseResource
)


class ImportShotgunShotsResource(BaseImportShotgunResource):

    def __init__(self):
        BaseImportShotgunResource.__init__(self)

    def prepare_import(self):
        self.shot_type = shots_service.get_shot_type()
        self.project_map = Project.get_id_map(field="name")
        self.asset_map = self.get_asset_map()
        self.sequence_map = self.get_sequence_map()

    def get_asset_map(self):
        assets = assets_service.get_assets()
        return {
            asset["shotgun_id"]: asset["id"] for asset in assets
        }

    def get_sequence_map(self):
        sequences = shots_service.get_sequences()
        return {
            sequence["shotgun_id"]: sequence["id"] for sequence in sequences
        }

    def extract_status_names(self, sg_projects):
        return {x["sg_status"] for x in sg_projects}

    def extract_data(self, sg_shot):
        (frame_in, frame_out) = self.extract_frame_range(sg_shot)
        custom_fields = self.extract_custom_data(sg_shot)
        project_id = self.get_project(sg_shot, self.project_map)
        sequence_id = self.get_sequence(sg_shot, self.sequence_map)
        assets = self.extract_assets(sg_shot, self.asset_map)

        shot_type = shots_service.get_shot_type()

        data = {
            "name": sg_shot["code"],
            "shotgun_id": sg_shot["id"],
            "project_id": project_id,
            "entity_type_id": shot_type["id"],
            "parent_id": sequence_id,
            "entities_out": assets
        }
        data_field_content = {
            "frame_in": frame_in,
            "frame_out": frame_out,
        }
        custom_fields.update(data_field_content)
        data["data"] = custom_fields
        return data

    def get_project(self, sg_shot, project_map):
        project_id = None
        if sg_shot["project"] is not None:
            project_id = project_map.get(sg_shot["project"]["name"], None)
        return project_id

    def get_sequence(self, sg_shot, sequence_map):
        sequence_id = None
        if "sg_sequence" in sg_shot and sg_shot["sg_sequence"] is not None:
            sequence_id = sequence_map.get(sg_shot["sg_sequence"]["id"], None)
        return sequence_id

    def extract_frame_range(self, sg_shot):
        frame_in = sg_shot["sg_cut_in"]
        frame_out = frame_in
        if frame_in is not None and sg_shot["sg_cut_duration"] is not None:
            frame_out = sg_shot["sg_cut_in"] + sg_shot["sg_cut_duration"]
        return (frame_in, frame_out)

    def extract_assets(self, sg_shot, asset_map):
        assets = []
        if "assets" in sg_shot and len(sg_shot["assets"]) > 0:
            for sg_asset in sg_shot["assets"]:
                entity_id = asset_map[sg_asset["id"]]
                asset = Entity.get(entity_id)
                assets.append(asset)
        return assets

    def extract_custom_data(self, sg_shot):
        return {
            k: v for k, v in sg_shot.items()
            if self.is_custom_field(k) and v is not None
        }

    def is_custom_field(self, name):
        non_custom_fields = [
            "sg_cut_in",
            "sg_cut_out",
            "sg_sequence",
        ]
        return name[:3] == "sg_" and name not in non_custom_fields

    def import_entry(self, data):
        shot = Entity.get_by(
            shotgun_id=data["shotgun_id"],
            entity_type_id=shots_service.get_shot_type()["id"]
        )

        if shot is None:
            shot = Entity(**data)
            shot.save()
            current_app.logger.info("Shot created: %s" % shot)

        else:
            if shot.data is None:
                shot.data = {}
            shot.update(data)
            shot.data.update(data["data"])
            shot.save()

            current_app.logger.info("Shot updated: %s" % shot)

        return shot


class ImportRemoveShotgunShotResource(ImportRemoveShotgunBaseResource):

    def __init__(self):
        ImportRemoveShotgunBaseResource.__init__(
            self,
            Entity,
            entity_type_id=shots_service.get_shot_type()["id"]
        )
