from osgeo import ogr, osr
from pkg_resources import resource_filename

from landsatlinks import utils

WRS2_FP = resource_filename('landsatlinks', 'assets/landsat_wrs2.gpkg')


class Aoi:
    def __init__(self, fp):
        self.fp = fp
        utils.validate_file_paths(self.fp, 'aoi', file=True, write=False)
        self.type = self.determine_aoi_type()

    def determine_aoi_type(self):
        if self.fp.endswith('.txt'):
            return 'txt'
        elif self.fp.endswith(('.shp', '.gpkg', '.geojson')):
            return 'vector'
        else:
            print(
                'Error: invalid file extension. Please use one of the following:\n'
                '.txt - text file containing one tile per line in the format PPPRRR (P = path, R = row)\n'
                '.shp, .gpkg, .geojson - vector file containing point, line, or polygon geometries.')
            exit(1)

    def prlist_from_txt(self):
        with open(self.fp) as file:
            pr_list = [line.rstrip() for line in file if line.strip()]
        if not utils.check_tile_validity(pr_list):
            print(
                'Error: invalid path/row values found in tile list.\n'
                'Make sure the file contains one tile per line in the format PPPRRR (P = path, R = row).')
            exit(1)
        return sorted(pr_list)

    def prlist_from_vector(self):
        wrs_ds = ogr.Open(WRS2_FP)
        wrs_layer = wrs_ds.GetLayer()
        aoi_ds = ogr.Open(self.fp)
        if not wrs_layer.GetSpatialRef().IsSame(aoi_ds.GetLayer().GetSpatialRef()):
            aoi_ds = self.reproject(aoi_ds, wrs_layer.GetSpatialRef())

        intersection_ds = self.intersect(aoi_ds, wrs_ds)
        intersection = intersection_ds.GetLayer()

        if intersection.GetFeatureCount() == 0:
            print('Error: AOI does not seem to intersect with WRS2 grid. Please check your input data.')

        pr_list = []
        feat = intersection.GetNextFeature()
        while feat:
            pr_list.append(feat.GetField('PRFID'))
            feat = intersection.GetNextFeature()

        return sorted(list(set(pr_list)))

    @property
    def get_footprints(self):
        if self.type == 'txt':
            return self.prlist_from_txt()
        elif self.type == 'vector':
            return self.prlist_from_vector()

    @staticmethod
    def reproject(in_ds, target_srs=None):
        """
        Reproject ogr.DataSource to a target projection
        :param in_ds: string or ogr.DataSource - path to source ds or ds
        :param target_srs: osr.SpatialReference - SRS to project to. Defaults to EPSG:4326
        :return: ogr.DataSource
        """

        in_layer = in_ds.GetLayer()

        # set spatial reference and transformation
        if not target_srs:
            target_srs = osr.SpatialReference()
            target_srs.ImportFromEPSG(4326)
        transform = osr.CoordinateTransformation(in_layer.GetSpatialRef(), target_srs)

        # create layer to copy information into
        driver = ogr.GetDriverByName('MEMORY')
        out_ds = driver.CreateDataSource('mem')
        # checks which geometry type we're looking at automatically layer.GetLayerDefn().GetGeomType()
        out_layer = out_ds.CreateLayer('', target_srs, in_layer.GetLayerDefn().GetGeomType())

        # apply transformation
        feat = in_layer.GetNextFeature()
        while feat:
            transformed = feat.GetGeometryRef()
            transformed.Transform(transform)

            geom = ogr.CreateGeometryFromWkb(transformed.ExportToWkb())
            defn = out_layer.GetLayerDefn()
            out_feat = ogr.Feature(defn)
            out_feat.SetGeometry(geom)
            out_layer.CreateFeature(out_feat)
            out_feat = None
            feat = in_layer.GetNextFeature()

        in_ds = None

        return out_ds

    @staticmethod
    def intersect(a_ds, b_ds):

        a_layer = a_ds.GetLayer()
        b_layer = b_ds.GetLayer()
        if not a_layer.GetSpatialRef().IsSame(b_layer.GetSpatialRef()):
            b_layer = None
            repr_ds = Aoi.reproject(b_ds, a_layer.GetSpatialRef())
            b_layer = repr_ds.GetLayer()

        out_ds = ogr.GetDriverByName('MEMORY').CreateDataSource('mem')
        out_layer = out_ds.CreateLayer('', a_layer.GetSpatialRef(), a_layer.GetLayerDefn().GetGeomType())
        a_layer.Intersection(b_layer, out_layer)

        return out_ds
