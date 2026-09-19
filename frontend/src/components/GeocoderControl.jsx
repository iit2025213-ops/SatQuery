import MapboxGeocoder from '@mapbox/mapbox-gl-geocoder';
import { useControl } from 'react-map-gl/mapbox';

export default function GeocoderControl(props) {
  useControl(
    () => {
      const geocoder = new MapboxGeocoder({
        ...props,
        accessToken: props.mapboxAccessToken,
        marker: false // We don't necessarily want a permanent marker, just to fly to the location
      });
      return geocoder;
    },
    { position: props.position }
  );
  return null;
}
