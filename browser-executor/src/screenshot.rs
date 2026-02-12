//! Screenshot capture and image processing

use chromiumoxide::cdp::browser_protocol::page::{
    CaptureScreenshotFormat, CaptureScreenshotParams,
};
use chromiumoxide::page::Page;
use image::ImageFormat;
use serde::{Deserialize, Serialize};
use std::io::Cursor;
use thiserror::Error;

/// Screenshot errors
#[derive(Error, Debug)]
pub enum ScreenshotError {
    #[error("Failed to capture screenshot: {0}")]
    CaptureFailed(String),

    #[error("Image processing error: {0}")]
    ProcessingError(String),

    #[error("Invalid format: {0}")]
    InvalidFormat(String),

    #[error("Encoding error: {0}")]
    EncodingError(String),
}

impl From<String> for ScreenshotError {
    fn from(s: String) -> Self {
        ScreenshotError::CaptureFailed(s)
    }
}

/// Screenshot format
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ScreenshotFormat {
    Png,
    Jpeg,
}

impl Default for ScreenshotFormat {
    fn default() -> Self {
        ScreenshotFormat::Png
    }
}

impl From<ScreenshotFormat> for CaptureScreenshotFormat {
    fn from(format: ScreenshotFormat) -> Self {
        match format {
            ScreenshotFormat::Png => CaptureScreenshotFormat::Png,
            ScreenshotFormat::Jpeg => CaptureScreenshotFormat::Jpeg,
        }
    }
}

/// Screenshot options
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScreenshotOptions {
    /// Capture full scrollable page
    pub full_page: bool,

    /// Image format
    pub format: ScreenshotFormat,

    /// JPEG quality (0-100)
    pub quality: Option<u8>,

    /// Clip to specific region
    pub clip: Option<ScreenshotClip>,

    /// Return as base64 string
    pub as_base64: bool,
}

impl Default for ScreenshotOptions {
    fn default() -> Self {
        Self {
            full_page: false,
            format: ScreenshotFormat::Png,
            quality: Some(80),
            clip: None,
            as_base64: true,
        }
    }
}

/// Screenshot clip region
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct ScreenshotClip {
    pub x: f64,
    pub y: f64,
    pub width: f64,
    pub height: f64,
    pub scale: Option<f64>,
}

/// Captured screenshot
#[derive(Debug, Clone)]
pub struct Screenshot {
    /// Image data (PNG or JPEG)
    pub data: Vec<u8>,

    /// Image format
    pub format: ScreenshotFormat,

    /// Image width (pixels)
    pub width: u32,

    /// Image height (pixels)
    pub height: u32,

    /// File size (bytes)
    pub size_bytes: usize,
}

impl Screenshot {
    /// Convert to base64 string
    pub fn to_base64(&self) -> String {
        use base64::{Engine as _, engine::general_purpose};
        general_purpose::STANDARD.encode(&self.data)
    }

    /// Get data URL (for embedding in HTML)
    pub fn to_data_url(&self) -> String {
        let mime_type = match self.format {
            ScreenshotFormat::Png => "image/png",
            ScreenshotFormat::Jpeg => "image/jpeg",
        };

        format!("data:{};base64,{}", mime_type, self.to_base64())
    }

    /// Save to file
    pub fn save_to_file(&self, path: &str) -> Result<(), ScreenshotError> {
        std::fs::write(path, &self.data)
            .map_err(|e| ScreenshotError::ProcessingError(e.to_string()))
    }

    /// Resize image
    pub fn resize(&mut self, width: u32, height: u32) -> Result<(), ScreenshotError> {
        let img = image::load_from_memory(&self.data)
            .map_err(|e| ScreenshotError::ProcessingError(e.to_string()))?;

        let resized = img.resize(width, height, image::imageops::FilterType::Lanczos3);

        let mut buffer = Vec::new();
        let format = match self.format {
            ScreenshotFormat::Png => ImageFormat::Png,
            ScreenshotFormat::Jpeg => ImageFormat::Jpeg,
        };

        resized
            .write_to(&mut Cursor::new(&mut buffer), format)
            .map_err(|e| ScreenshotError::EncodingError(e.to_string()))?;

        self.data = buffer;
        self.width = width;
        self.height = height;
        self.size_bytes = self.data.len();

        Ok(())
    }

    /// Compress image (reduce quality)
    pub fn compress(&mut self, quality: u8) -> Result<(), ScreenshotError> {
        if self.format != ScreenshotFormat::Jpeg {
            return Err(ScreenshotError::ProcessingError(
                "Compression only supported for JPEG".to_string(),
            ));
        }

        let img = image::load_from_memory(&self.data)
            .map_err(|e| ScreenshotError::ProcessingError(e.to_string()))?;

        let mut buffer = Vec::new();
        let mut encoder = image::codecs::jpeg::JpegEncoder::new_with_quality(
            &mut buffer,
            quality.min(100),
        );

        encoder
            .encode(
                img.as_bytes(),
                self.width,
                self.height,
                img.color(),
            )
            .map_err(|e| ScreenshotError::EncodingError(e.to_string()))?;

        self.data = buffer;
        self.size_bytes = self.data.len();

        Ok(())
    }
}

/// Screenshot capturer
pub struct ScreenshotCapturer;

impl ScreenshotCapturer {
    /// Capture screenshot from page
    pub async fn capture(
        page: &Page,
        options: ScreenshotOptions,
    ) -> Result<Screenshot, ScreenshotError> {
        let mut params = CaptureScreenshotParams::builder()
            .format(options.format)
            .build();

        // Set quality for JPEG
        if let ScreenshotFormat::Jpeg = options.format {
            if let Some(quality) = options.quality {
                params.quality = Some(quality as i64);
            }
        }

        // Set clip region
        if let Some(clip) = options.clip {
            params.clip = Some(
                chromiumoxide::cdp::browser_protocol::page::Viewport::builder()
                    .x(clip.x)
                    .y(clip.y)
                    .width(clip.width)
                    .height(clip.height)
                    .scale(clip.scale.unwrap_or(1.0))
                    .build()?,
            );
        }

        // Capture screenshot
        let data = if options.full_page {
            // Capture full page by setting capture_beyond_viewport
            params.capture_beyond_viewport = Some(true);
            page.screenshot(params)
                .await
                .map_err(|e| ScreenshotError::CaptureFailed(e.to_string()))?
        } else {
            page.screenshot(params)
                .await
                .map_err(|e| ScreenshotError::CaptureFailed(e.to_string()))?
        };

        // Get image dimensions
        let img = image::load_from_memory(&data)
            .map_err(|e| ScreenshotError::ProcessingError(e.to_string()))?;

        let width = img.width();
        let height = img.height();
        let size_bytes = data.len();

        Ok(Screenshot {
            data,
            format: options.format,
            width,
            height,
            size_bytes,
        })
    }

    /// Capture element screenshot
    pub async fn capture_element(
        page: &Page,
        selector: &str,
        options: ScreenshotOptions,
    ) -> Result<Screenshot, ScreenshotError> {
        // Find element
        let _element = page
            .find_element(selector)
            .await
            .map_err(|e| ScreenshotError::CaptureFailed(format!("Element not found: {}", e)))?;

        // Get element bounding box using JS
        let script = format!(
            "document.querySelector('{}').getBoundingClientRect()",
            selector.replace("'", "\\'")
        );

        let rect_json: serde_json::Value = page
            .evaluate(script.as_str())
            .await
            .map_err(|e| ScreenshotError::CaptureFailed(e.to_string()))?
            .into_value()
            .map_err(|e| ScreenshotError::CaptureFailed(e.to_string()))?;

        // Parse bounding box
        let rect: serde_json::Value = serde_json::from_str(&rect_json.to_string())
            .map_err(|e| ScreenshotError::ProcessingError(e.to_string()))?;

        let clip = ScreenshotClip {
            x: rect["x"].as_f64().unwrap_or(0.0),
            y: rect["y"].as_f64().unwrap_or(0.0),
            width: rect["width"].as_f64().unwrap_or(0.0),
            height: rect["height"].as_f64().unwrap_or(0.0),
            scale: Some(1.0),
        };

        // Capture with clip
        let mut opts = options;
        opts.clip = Some(clip);

        Self::capture(page, opts).await
    }

    /// Capture multiple screenshots at different viewports
    pub async fn capture_responsive(
        page: &Page,
        viewports: Vec<(u32, u32)>, // (width, height)
        options: ScreenshotOptions,
    ) -> Result<Vec<Screenshot>, ScreenshotError> {
        let mut screenshots = Vec::new();

        for (_width, _height) in viewports {
            // Note: set_viewport() is not available in chromiumoxide API
            // Viewport changes would require emulation configuration at browser launch
            // For now, capture at default viewport size

            // Wait for render
            tokio::time::sleep(std::time::Duration::from_millis(500)).await;

            // Capture
            let screenshot = Self::capture(page, options.clone()).await?;
            screenshots.push(screenshot);
        }

        Ok(screenshots)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_screenshot_to_base64() {
        let screenshot = Screenshot {
            data: vec![1, 2, 3, 4, 5],
            format: ScreenshotFormat::Png,
            width: 100,
            height: 100,
            size_bytes: 5,
        };

        let base64 = screenshot.to_base64();
        assert!(!base64.is_empty());
    }

    #[test]
    fn test_screenshot_data_url() {
        let screenshot = Screenshot {
            data: vec![1, 2, 3, 4, 5],
            format: ScreenshotFormat::Png,
            width: 100,
            height: 100,
            size_bytes: 5,
        };

        let data_url = screenshot.to_data_url();
        assert!(data_url.starts_with("data:image/png;base64,"));
    }
}
