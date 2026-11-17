/** House styles. Photos are listed front first. Plans are line drawings in Drawings.tsx. */
export type StyleKey = 'pop' | 'mcm' | 'craftsman'

export type StylePhoto = { src: string; width: number; height: number }

export type HouseStyle = {
  key: StyleKey
  name: string
  tagline: string
  photos: StylePhoto[]
  photosTwo?: StylePhoto[]
}

export const styles: HouseStyle[] = [
  {
    key: 'pop',
    name: 'Quarter Century Pop',
    tagline: 'Soft corners, big glass, clean white panels.',
    photos: [
      { src: '/styles/pop-front.png', width: 1536, height: 1024 },
      { src: '/styles/pop-angle.png', width: 1536, height: 1024 },
    ],
  },
  {
    key: 'mcm',
    name: 'Mid-Century Modern',
    tagline: 'Warm wood, a low flat roof and walls of glass.',
    photos: [
      { src: '/styles/mcm-1story-front.jpg', width: 1408, height: 768 },
    ],
    photosTwo: [
      { src: '/styles/mcm-2story-front.jpg', width: 1408, height: 768 },
      { src: '/styles/mcm-2story-wing.jpg', width: 1408, height: 768 },
      { src: '/styles/mcm-2story-aframe.jpg', width: 1408, height: 768 },
    ],
  },
  {
    key: 'craftsman',
    name: 'Modern Craftsman',
    tagline: 'Gabled roof, a real front porch, classic lines.',
    photos: [
      { src: '/styles/craftsman-front.jpg', width: 2816, height: 1536 },
      { src: '/styles/craftsman-angle.jpg', width: 2816, height: 1536 },
    ],
  },
]

export function styleByKey(key: string | null | undefined): HouseStyle {
  return styles.find((s) => s.key === key) ?? styles[0]
}

export function photosFor(style: HouseStyle, stories: number | null | undefined): StylePhoto[] {
  if (stories === 2 && style.photosTwo?.length) return style.photosTwo
  return style.photos
}

export function homeLabel(modelName: string, styleName: string, stories: number | null | undefined): string {
  return `${modelName} · ${styleName}${stories === 2 ? ' · Two story' : ''}`
}
