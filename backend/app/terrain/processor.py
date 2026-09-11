# app/terrain/processor.py

"""
Terrain Processor — Phase 8

Generates 2D terrain visualizations (hillshade + contours) and
3D terrain meshes (glTF/GLB) from DEM + satellite imagery.

Source of truth: 6-9.md Phase 8 architecture.
"""

import logging
import io
import os
import struct
import json
import asyncio
from typing import Tuple, Optional, List

import numpy as np
from scipy import ndimage

logger = logging.getLogger("satquery")


class TerrainProcessor:
    """Process DEM and imagery into terrain visualizations."""

    # ------------------------------------------------------------------
    # 2D Terrain
    # ------------------------------------------------------------------

    @staticmethod
    async def generate_2d_terrain(
        dem_data: np.ndarray,
        options: dict = None,
    ) -> Tuple[np.ndarray, np.ndarray, dict]:
        """
        Generate 2D terrain visualization from a DEM numpy array.

        Args:
            dem_data: 2D numpy array of elevation values (metres).
            options: Hillshade/contour parameters.

        Returns:
            (hillshade_array, contour_array, elevation_stats)
        """
        if options is None:
            options = {}

        azimuth = options.get("hillshade_azimuth", 315)
        altitude = options.get("hillshade_altitude", 45)
        contrast = options.get("hillshade_contrast", 1.0)
        contour_interval = options.get("contour_interval", 10)

        try:
            # Replace NaN with 0 for safe computation
            dem_clean = np.nan_to_num(dem_data, nan=0.0)

            # Generate hillshade
            hillshade = TerrainProcessor._generate_hillshade(
                dem_clean,
                azimuth=azimuth,
                altitude=altitude,
                contrast=contrast,
            )

            # Generate contours
            contours = TerrainProcessor._generate_contours(
                dem_clean,
                interval=contour_interval,
            )

            # Calculate statistics
            valid = dem_data[~np.isnan(dem_data)] if np.any(np.isnan(dem_data)) else dem_data
            stats = {
                "min_elevation_m": float(np.min(valid)),
                "max_elevation_m": float(np.max(valid)),
                "mean_elevation_m": float(np.mean(valid)),
                "std_elevation_m": float(np.std(valid)),
                "relief_m": float(np.max(valid) - np.min(valid)),
                "hillshade_shape": list(hillshade.shape),
                "contour_interval_m": contour_interval,
            }

            logger.info(f"✅ Generated 2D terrain — stats: {stats}")
            return hillshade, contours, stats

        except Exception as e:
            logger.error(f"❌ Error generating 2D terrain: {e}")
            return np.array([]), np.array([]), {}

    @staticmethod
    def _generate_hillshade(
        dem_data: np.ndarray,
        azimuth: float = 315,
        altitude: float = 45,
        contrast: float = 1.0,
    ) -> np.ndarray:
        """
        Generate hillshade (shaded relief) from DEM.

        Uses slope + aspect calculation with configurable light direction.
        """
        # Convert light source angles to radians
        azimuth_rad = np.radians(360.0 - azimuth + 90)
        altitude_rad = np.radians(altitude)

        # Calculate gradients (slope in x and y)
        dy, dx = np.gradient(dem_data)

        # Calculate slope and aspect
        slope = np.pi / 2.0 - np.arctan(np.sqrt(dx * dx + dy * dy))
        aspect = np.arctan2(-dy, dx)

        # Calculate shaded relief
        shaded = (
            np.sin(altitude_rad) * np.sin(slope)
            + np.cos(altitude_rad) * np.cos(slope)
            * np.cos(azimuth_rad - aspect)
        )

        # Normalize to 0-255
        shaded = (shaded - shaded.min()) / (shaded.max() - shaded.min() + 1e-10)

        # Apply contrast
        if contrast != 1.0:
            shaded = np.clip(shaded * contrast, 0, 1)

        shaded = (shaded * 255).astype(np.uint8)

        return shaded

    @staticmethod
    def _generate_contours(
        dem_data: np.ndarray,
        interval: int = 10,
    ) -> np.ndarray:
        """
        Generate contour lines from DEM.

        Returns a binary uint8 image where contour lines are 255.
        """
        min_elev = float(np.min(dem_data))
        max_elev = float(np.max(dem_data))

        if max_elev - min_elev < interval:
            # Terrain too flat for contours at this interval
            return np.zeros_like(dem_data, dtype=np.uint8)

        levels = np.arange(min_elev, max_elev, interval)

        contours = np.zeros_like(dem_data, dtype=np.uint8)
        for level in levels:
            # Find pixels near this elevation (within ±1.5 m)
            level_mask = np.abs(dem_data - level) < 1.5
            contours[level_mask] = 255

        return contours

    # ------------------------------------------------------------------
    # 3D Terrain
    # ------------------------------------------------------------------

    @staticmethod
    async def generate_3d_terrain(
        dem_data: np.ndarray,
        aoi_bbox: List[float],
        texture_rgb: Optional[np.ndarray] = None,
        options: dict = None,
    ) -> Tuple[bytes, dict]:
        """
        Generate 3D terrain mesh from DEM.

        Args:
            dem_data: 2D numpy array of elevation values.
            aoi_bbox: [minx, miny, maxx, maxy] in geographic coords.
            texture_rgb: Optional (H, W, 3) uint8 RGB texture array.
            options: Mesh generation parameters.

        Returns:
            (glb_bytes, mesh_metadata)
        """
        if options is None:
            options = {}

        exaggeration = options.get("elevation_exaggeration", 1.5)
        max_resolution = options.get("mesh_resolution", 256)

        try:
            dem_clean = np.nan_to_num(dem_data, nan=0.0)

            # Generate mesh
            vertices, faces, normals = TerrainProcessor._dem_to_mesh(
                dem_clean,
                exaggeration=exaggeration,
                max_vertices=max_resolution,
            )

            # Generate UV coordinates
            uv_coords = TerrainProcessor._generate_uv_coordinates(dem_clean.shape)

            # Export as GLB
            glb_bytes = TerrainProcessor._export_glb(
                vertices, faces, normals, uv_coords, texture_rgb
            )

            metadata = {
                "vertex_count": int(len(vertices)),
                "triangle_count": int(len(faces)),
                "file_size_bytes": len(glb_bytes),
                "file_size_mb": round(len(glb_bytes) / (1024 * 1024), 2),
                "exaggeration": exaggeration,
                "bounds": {
                    "minx": aoi_bbox[0],
                    "miny": aoi_bbox[1],
                    "maxx": aoi_bbox[2],
                    "maxy": aoi_bbox[3],
                },
                "elevation_range_m": {
                    "min": float(np.min(dem_clean)),
                    "max": float(np.max(dem_clean)),
                },
            }

            logger.info(
                f"✅ Generated 3D mesh — {metadata['vertex_count']} vertices, "
                f"{metadata['triangle_count']} triangles, "
                f"{metadata['file_size_mb']} MB"
            )
            return glb_bytes, metadata

        except Exception as e:
            logger.error(f"❌ Error generating 3D terrain: {e}")
            return b"", {}

    @staticmethod
    def _dem_to_mesh(
        dem_data: np.ndarray,
        exaggeration: float = 1.5,
        max_vertices: int = 256,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Convert DEM raster to 3D mesh vertices, faces, and normals.
        """
        # Downsample if needed
        if dem_data.shape[0] > max_vertices or dem_data.shape[1] > max_vertices:
            scale = max_vertices / max(dem_data.shape)
            dem_data = ndimage.zoom(dem_data, scale, order=1)

        height, width = dem_data.shape

        # Create grid of x, y coordinates (normalised 0-1)
        x = np.linspace(0, 1, width, dtype=np.float32)
        y = np.linspace(0, 1, height, dtype=np.float32)
        xx, yy = np.meshgrid(x, y)

        # Normalise elevation to a visible range and apply exaggeration
        z_min = dem_data.min()
        z_max = dem_data.max()
        z_range = z_max - z_min if z_max != z_min else 1.0
        zz = ((dem_data - z_min) / z_range) * exaggeration * 0.3  # scale to ~30% of x/y

        # Flatten to vertex list — (x, z_up, -y) for standard 3D orientation
        vertices = np.column_stack([
            xx.ravel().astype(np.float32),
            zz.ravel().astype(np.float32),
            -yy.ravel().astype(np.float32),
        ])

        # Create triangle indices from grid
        faces = []
        for i in range(height - 1):
            for j in range(width - 1):
                v0 = i * width + j
                v1 = i * width + j + 1
                v2 = (i + 1) * width + j
                v3 = (i + 1) * width + j + 1

                faces.append([v0, v1, v2])
                faces.append([v1, v3, v2])

        faces = np.array(faces, dtype=np.uint32)

        # Calculate per-vertex normals
        normals = TerrainProcessor._calculate_normals(vertices, faces)

        return vertices, faces, normals

    @staticmethod
    def _calculate_normals(
        vertices: np.ndarray, faces: np.ndarray
    ) -> np.ndarray:
        """Calculate smooth per-vertex normals from triangle faces."""
        normals = np.zeros_like(vertices)

        for face in faces:
            v0, v1, v2 = vertices[face[0]], vertices[face[1]], vertices[face[2]]
            edge1 = v1 - v0
            edge2 = v2 - v0
            face_normal = np.cross(edge1, edge2)
            normals[face[0]] += face_normal
            normals[face[1]] += face_normal
            normals[face[2]] += face_normal

        # Normalise
        lengths = np.linalg.norm(normals, axis=1, keepdims=True)
        lengths[lengths == 0] = 1.0
        normals = normals / lengths

        return normals.astype(np.float32)

    @staticmethod
    def _generate_uv_coordinates(dem_shape: Tuple) -> np.ndarray:
        """Generate UV texture coordinates mapped 0-1 across the mesh."""
        height, width = dem_shape
        u = np.linspace(0, 1, width, dtype=np.float32)
        v = np.linspace(0, 1, height, dtype=np.float32)
        uu, vv = np.meshgrid(u, v)
        return np.column_stack([uu.ravel(), vv.ravel()])

    # ------------------------------------------------------------------
    # glTF / GLB Export (minimal, no external dep required)
    # ------------------------------------------------------------------

    @staticmethod
    def _export_glb(
        vertices: np.ndarray,
        faces: np.ndarray,
        normals: np.ndarray,
        uv_coords: np.ndarray,
        texture_rgb: Optional[np.ndarray] = None,
    ) -> bytes:
        """
        Export mesh as a binary GLB (glTF 2.0).

        Uses trimesh if available, otherwise falls back to a minimal
        hand-built GLB so the system works without heavy deps.
        """
        try:
            import trimesh

            mesh = trimesh.Trimesh(
                vertices=vertices,
                faces=faces,
                vertex_normals=normals,
            )

            # Attach texture as vertex colours if provided
            if texture_rgb is not None and texture_rgb.size > 0:
                try:
                    h, w, _ = texture_rgb.shape
                    # Map UV to pixel coords
                    u_px = (uv_coords[:, 0] * (w - 1)).astype(int)
                    v_px = (uv_coords[:, 1] * (h - 1)).astype(int)
                    u_px = np.clip(u_px, 0, w - 1)
                    v_px = np.clip(v_px, 0, h - 1)
                    colours = texture_rgb[v_px, u_px]
                    alpha = np.full((len(colours), 1), 255, dtype=np.uint8)
                    mesh.visual.vertex_colors = np.hstack([colours, alpha])
                except Exception:
                    pass

            glb_bytes = mesh.export(file_type="glb")
            return glb_bytes

        except ImportError:
            logger.warning("trimesh not installed — using minimal GLB export")
            return TerrainProcessor._minimal_glb(vertices, faces, normals)

    @staticmethod
    def _minimal_glb(
        vertices: np.ndarray,
        faces: np.ndarray,
        normals: np.ndarray,
    ) -> bytes:
        """
        Build a minimal valid GLB file without any external library.

        This is a fallback so the system doesn't break if trimesh
        isn't installed. It produces a grey untextured mesh.
        """
        # Binary buffers
        vert_bytes = vertices.astype(np.float32).tobytes()
        norm_bytes = normals.astype(np.float32).tobytes()
        face_bytes = faces.astype(np.uint32).tobytes()
        bin_data = vert_bytes + norm_bytes + face_bytes

        vert_count = len(vertices)
        face_count = len(faces)

        vert_min = vertices.min(axis=0).tolist()
        vert_max = vertices.max(axis=0).tolist()

        gltf_json = {
            "asset": {"version": "2.0", "generator": "SatQuery-Terrain"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0}],
            "meshes": [
                {
                    "primitives": [
                        {
                            "attributes": {"POSITION": 0, "NORMAL": 1},
                            "indices": 2,
                        }
                    ]
                }
            ],
            "accessors": [
                {
                    "bufferView": 0,
                    "componentType": 5126,
                    "count": vert_count,
                    "type": "VEC3",
                    "min": vert_min,
                    "max": vert_max,
                },
                {
                    "bufferView": 1,
                    "componentType": 5126,
                    "count": vert_count,
                    "type": "VEC3",
                },
                {
                    "bufferView": 2,
                    "componentType": 5125,
                    "count": face_count * 3,
                    "type": "SCALAR",
                },
            ],
            "bufferViews": [
                {"buffer": 0, "byteOffset": 0, "byteLength": len(vert_bytes)},
                {
                    "buffer": 0,
                    "byteOffset": len(vert_bytes),
                    "byteLength": len(norm_bytes),
                },
                {
                    "buffer": 0,
                    "byteOffset": len(vert_bytes) + len(norm_bytes),
                    "byteLength": len(face_bytes),
                },
            ],
            "buffers": [{"byteLength": len(bin_data)}],
        }

        json_str = json.dumps(gltf_json, separators=(",", ":"))
        # Pad JSON to 4-byte alignment
        while len(json_str) % 4 != 0:
            json_str += " "
        json_bytes = json_str.encode("utf-8")

        # Pad binary to 4-byte alignment
        while len(bin_data) % 4 != 0:
            bin_data += b"\x00"

        # GLB header
        glb = bytearray()
        # Magic
        glb += struct.pack("<I", 0x46546C67)  # glTF
        # Version
        glb += struct.pack("<I", 2)
        # Total length (filled later)
        total_length = 12 + 8 + len(json_bytes) + 8 + len(bin_data)
        glb += struct.pack("<I", total_length)

        # JSON chunk
        glb += struct.pack("<I", len(json_bytes))
        glb += struct.pack("<I", 0x4E4F534A)  # JSON
        glb += json_bytes

        # BIN chunk
        glb += struct.pack("<I", len(bin_data))
        glb += struct.pack("<I", 0x004E4942)  # BIN
        glb += bin_data

        return bytes(glb)

    # ------------------------------------------------------------------
    # LOD generation
    # ------------------------------------------------------------------

    @staticmethod
    def generate_lod_meshes(
        dem_data: np.ndarray,
        aoi_bbox: List[float],
        lod_levels: List[int] = None,
    ) -> List[Tuple[bytes, dict]]:
        """
        Generate multiple Level-of-Detail meshes.

        Default LODs: 256 (high), 128 (medium), 64 (low).
        """
        if lod_levels is None:
            lod_levels = [256, 128, 64]

        results = []
        for resolution in lod_levels:
            loop = asyncio.new_event_loop()
            glb, meta = loop.run_until_complete(
                TerrainProcessor.generate_3d_terrain(
                    dem_data, aoi_bbox, options={"mesh_resolution": resolution}
                )
            )
            loop.close()
            meta["lod_resolution"] = resolution
            results.append((glb, meta))

        return results
