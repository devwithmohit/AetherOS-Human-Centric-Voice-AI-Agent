/// Audio buffer module for storing rolling audio data
///
/// Implements a ring buffer for real-time audio processing.
/// Designed to hold 3 seconds of 16kHz PCM audio (~96KB).

use cache_padded::CachePadded;
use ringbuf::traits::{Consumer, Observer, Producer, Split};
use ringbuf::HeapRb;
use std::sync::Mutex;
use thiserror::Error;
use tracing::{debug, warn};

/// Audio sample format (16-bit PCM)
pub type AudioSample = i16;

/// Ring buffer size: 3 seconds at 16kHz sample rate
pub const BUFFER_DURATION_SECS: usize = 3;
pub const SAMPLE_RATE: usize = 16000;
pub const BUFFER_SIZE: usize = BUFFER_DURATION_SECS * SAMPLE_RATE; // 48,000 samples

#[derive(Error, Debug)]
pub enum AudioBufferError {
    #[error("Buffer overflow: attempted to write {0} samples, but only {1} slots available")]
    Overflow(usize, usize),

    #[error("Buffer underflow: attempted to read {0} samples, but only {1} available")]
    Underflow(usize, usize),

    #[error("Invalid buffer size: {0}")]
    InvalidSize(usize),
}

type RingBuffer = HeapRb<AudioSample>;
type RingProducer = <RingBuffer as Split>::Prod;
type RingConsumer = <RingBuffer as Split>::Cons;

/// Ring buffer for audio samples
/// Uses separate producer and consumer for thread-safe access
pub struct AudioBuffer {
    producer: CachePadded<Mutex<RingProducer>>,
    consumer: CachePadded<Mutex<RingConsumer>>,
    sample_rate: usize,
    channels: usize,
}

impl AudioBuffer {
    /// Create a new audio buffer with default 3-second capacity
    pub fn new() -> Self {
        Self::with_capacity(BUFFER_SIZE)
    }

    /// Create a buffer with custom capacity
    pub fn with_capacity(capacity: usize) -> Self {
        debug!("Creating audio buffer with capacity: {} samples", capacity);

        let rb = HeapRb::<AudioSample>::new(capacity);
        let (producer, consumer) = rb.split();

        Self {
            producer: CachePadded::new(Mutex::new(producer)),
            consumer: CachePadded::new(Mutex::new(consumer)),
            sample_rate: SAMPLE_RATE,
            channels: 1, // Mono audio
        }
    }

    /// Write audio samples to the buffer (non-blocking)
    ///
    /// Returns the number of samples successfully written.
    /// If buffer is full, oldest samples are overwritten.
    pub fn write(&mut self, samples: &[AudioSample]) -> usize {
        let mut producer = self.producer.lock().unwrap();

        let available_space = producer.vacant_len();
        let to_write = samples.len();

        if to_write > available_space {
            // Need to drop oldest samples to make room
            let to_drop = to_write - available_space;
            let mut consumer = self.consumer.lock().unwrap();
            consumer.skip(to_drop);
            drop(consumer); // Release lock

            warn!(
                "Buffer full, dropping {} oldest samples to make room",
                to_drop
            );
        }

        // Write new samples
        let written = producer.push_slice(samples);
        debug!("Wrote {} samples to buffer", written);

        written
    }

    /// Read samples from the buffer without removing them (peek)
    pub fn peek(&self, count: usize) -> Vec<AudioSample> {
        let consumer = self.consumer.lock().unwrap();
        let available = consumer.occupied_len();
        let to_read = count.min(available);

        let mut result = Vec::with_capacity(to_read);

        // Read directly into iterator
        for item in consumer.iter().take(to_read) {
            result.push(*item);
        }

        result
    }

    /// Read and remove samples from the buffer
    pub fn read(&mut self, count: usize) -> Result<Vec<AudioSample>, AudioBufferError> {
        let mut consumer = self.consumer.lock().unwrap();
        let available = consumer.occupied_len();

        if count > available {
            return Err(AudioBufferError::Underflow(count, available));
        }

        let mut result = vec![0; count];
        let read = consumer.pop_slice(&mut result);
        result.truncate(read);

        debug!("Read {} samples from buffer", read);
        Ok(result)
    }

    /// Get the number of samples currently in the buffer
    pub fn len(&self) -> usize {
        let consumer = self.consumer.lock().unwrap();
        consumer.occupied_len()
    }

    /// Check if buffer is empty
    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    /// Get buffer capacity
    pub fn capacity(&self) -> usize {
        let consumer = self.consumer.lock().unwrap();
        consumer.capacity().get()
    }

    /// Get the amount of free space in the buffer
    pub fn free_space(&self) -> usize {
        let producer = self.producer.lock().unwrap();
        producer.vacant_len()
    }

    /// Clear all data from the buffer
    pub fn clear(&mut self) {
        let mut consumer = self.consumer.lock().unwrap();
        let occupied = consumer.occupied_len();
        consumer.skip(occupied);
        debug!("Cleared audio buffer");
    }

    /// Get the sample rate
    pub fn sample_rate(&self) -> usize {
        self.sample_rate
    }

    /// Get the number of channels
    pub fn channels(&self) -> usize {
        self.channels
    }

    /// Get duration of audio currently in buffer (in seconds)
    pub fn duration_secs(&self) -> f32 {
        self.len() as f32 / self.sample_rate as f32
    }
}

impl Default for AudioBuffer {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_relative_eq;

    #[test]
    fn test_buffer_creation() {
        let buffer = AudioBuffer::new();
        assert_eq!(buffer.capacity(), BUFFER_SIZE);
        assert_eq!(buffer.len(), 0);
        assert!(buffer.is_empty());
        assert_eq!(buffer.sample_rate(), SAMPLE_RATE);
    }

    #[test]
    fn test_write_and_read() {
        let mut buffer = AudioBuffer::with_capacity(1000);
        let samples: Vec<i16> = (0..100).map(|i| i as i16).collect();

        let written = buffer.write(&samples);
        assert_eq!(written, 100);
        assert_eq!(buffer.len(), 100);

        let read = buffer.read(50).unwrap();
        assert_eq!(read.len(), 50);
        assert_eq!(buffer.len(), 50);
        assert_eq!(read[0], 0);
        assert_eq!(read[49], 49);
    }

    #[test]
    fn test_peek_does_not_remove() {
        let mut buffer = AudioBuffer::with_capacity(1000);
        let samples: Vec<i16> = vec![1, 2, 3, 4, 5];

        buffer.write(&samples);
        let peeked = buffer.peek(3);

        assert_eq!(peeked, vec![1, 2, 3]);
        assert_eq!(buffer.len(), 5); // No samples removed
    }

    #[test]
    fn test_buffer_overflow() {
        let mut buffer = AudioBuffer::with_capacity(100);
        let samples: Vec<i16> = vec![1; 150];

        // Writing more than capacity should drop oldest samples
        let written = buffer.write(&samples);
        assert_eq!(written, 150);
        assert_eq!(buffer.len(), 100); // Only capacity remains
    }

    #[test]
    fn test_buffer_underflow() {
        let mut buffer = AudioBuffer::with_capacity(100);
        let samples: Vec<i16> = vec![1; 50];
        buffer.write(&samples);

        // Try to read more than available
        let result = buffer.read(100);
        assert!(result.is_err());

        match result {
            Err(AudioBufferError::Underflow(requested, available)) => {
                assert_eq!(requested, 100);
                assert_eq!(available, 50);
            }
            _ => panic!("Expected Underflow error"),
        }
    }

    #[test]
    fn test_clear() {
        let mut buffer = AudioBuffer::with_capacity(1000);
        buffer.write(&vec![1; 500]);
        assert_eq!(buffer.len(), 500);

        buffer.clear();
        assert_eq!(buffer.len(), 0);
        assert!(buffer.is_empty());
    }

    #[test]
    fn test_duration_calculation() {
        let mut buffer = AudioBuffer::new();
        buffer.write(&vec![0; SAMPLE_RATE]); // 1 second of audio

        assert_relative_eq!(buffer.duration_secs(), 1.0, epsilon = 0.01);
    }

    #[test]
    fn test_ring_buffer_wrapping() {
        let mut buffer = AudioBuffer::with_capacity(10);

        // Fill buffer
        buffer.write(&vec![1; 10]);
        assert_eq!(buffer.len(), 10);

        // Write more data (should wrap around)
        buffer.write(&vec![2; 5]);
        assert_eq!(buffer.len(), 10); // Still at capacity

        // Read should get the newer data
        let data = buffer.peek(10);
        // First 5 should be 2s (newer), last 5 should be 1s
        assert_eq!(data[0], 2);
    }

    #[test]
    fn test_free_space() {
        let mut buffer = AudioBuffer::with_capacity(100);
        assert_eq!(buffer.free_space(), 100);

        buffer.write(&vec![1; 30]);
        assert_eq!(buffer.free_space(), 70);

        buffer.read(10).unwrap();
        assert_eq!(buffer.free_space(), 80);
    }
}
