# Fork of google/spatial-media

* Intention to use this library to detect 360 video, instead of inject.
* It does not interact with audio
* It prints out video track data in JSON


Good file
```
> python spatial-media bob.mp4
{"video": {"Track 0": {"Spherical": "true", "Stitched": "true", "StitchingSoftware": " Samsung Gear 360 ActionDirector-V1.0.0.2005 ", "ProjectionType": "equirectangular"}}}

```

Non-360 File:
```
> python spatial-media not360.mp4
{"video": {}}

```

Errors:
```
> python spatial-media invalidfile.mp4
{"video": {"error": {"error": "No permissions to access file"}}}

```