import os
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

def assemble_video(asset_dir, script_file, audio_file, output_file):
    """
    Assembles the final video from assets, script, and audio.
    """
    print(f"Assembling video using assets from {asset_dir} and audio from {audio_file}")
    
    if not os.path.exists(audio_file):
        print(f"Error: Audio file {audio_file} not found.")
        return

    # Load audio
    audio_clip = AudioFileClip(audio_file)
    total_duration = audio_clip.duration
    
    # Load images
    image_files = sorted([os.path.join(asset_dir, f) for f in os.listdir(asset_dir) if f.endswith('.png')])
    
    if not image_files:
        print("No assets found to assemble.")
        return

    # Calculate duration per image to match audio length
    duration_per_image = total_duration / len(image_files)
    
    print(f"Total duration: {total_duration}s, Images: {len(image_files)}, Duration per image: {duration_per_image}s")
    
    clips = [ImageClip(m).with_duration(duration_per_image) for m in image_files]
    
    # Create final video
    final_video = concatenate_videoclips(clips, method="compose")
    final_video = final_video.with_audio(audio_clip)
    
    # Write output
    final_video.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac")
    
    print(f"Video assembled: {output_file}")
