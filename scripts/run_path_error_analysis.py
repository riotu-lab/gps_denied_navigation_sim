#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_srvs.srv import SetBool
import time
import argparse

class PathErrorController(Node):
    def __init__(self):
        super().__init__('path_error_controller')
        
        # Service clients
        self.start_client = self.create_client(SetBool, 'start_error_recording')
        self.stop_client = self.create_client(SetBool, 'stop_error_recording')
        self.reset_client = self.create_client(SetBool, 'reset_error_data')
        
        # Wait for services
        self.get_logger().info("Waiting for path error calculator services...")
        self.start_client.wait_for_service(timeout_sec=10.0)
        self.stop_client.wait_for_service(timeout_sec=10.0)
        self.reset_client.wait_for_service(timeout_sec=10.0)
        self.get_logger().info("Services found!")

    def start_recording(self):
        """Start error recording"""
        request = SetBool.Request()
        request.data = True
        
        future = self.start_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        
        if future.result() is not None:
            response = future.result()
            if response.success:
                self.get_logger().info(f"✓ Started recording: {response.message}")
                return True
            else:
                self.get_logger().error(f"✗ Failed to start recording: {response.message}")
                return False
        else:
            self.get_logger().error("✗ Service call failed")
            return False

    def stop_recording(self):
        """Stop error recording and generate summary"""
        request = SetBool.Request()
        request.data = True
        
        future = self.stop_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        
        if future.result() is not None:
            response = future.result()
            if response.success:
                self.get_logger().info(f"✓ Stopped recording: {response.message}")
                return True
            else:
                self.get_logger().error(f"✗ Failed to stop recording: {response.message}")
                return False
        else:
            self.get_logger().error("✗ Service call failed")
            return False

    def reset_data(self):
        """Reset accumulated error data"""
        request = SetBool.Request()
        request.data = True
        
        future = self.reset_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        
        if future.result() is not None:
            response = future.result()
            if response.success:
                self.get_logger().info(f"✓ Reset data: {response.message}")
                return True
            else:
                self.get_logger().error(f"✗ Failed to reset data: {response.message}")
                return False
        else:
            self.get_logger().error("✗ Service call failed")
            return False

def print_usage():
    print("\n" + "="*60)
    print("Path Error Analysis Controller")
    print("="*60)
    print("\nThis script helps you control the path error calculator node.")
    print("\nReal-time error topics (you can echo these):")
    print("  ros2 topic echo /path_error/position_error")
    print("  ros2 topic echo /path_error/orientation_error")
    print("  ros2 topic echo /path_error/velocity_error")
    print("  ros2 topic echo /path_error/cumulative_error")
    print("\nInput topics (make sure these are publishing):")
    print("  /target/gt_path        - Ground truth path")
    print("  /mins/imu/path         - MINS estimated path")
    print("\nOutput files (will be saved to specified directory):")
    print("  path_error_analysis.csv         - Detailed error data")
    print("  path_error_analysis_summary.txt - Statistical summary")
    print("\n" + "="*60)

def main():
    parser = argparse.ArgumentParser(description='Control path error analysis recording')
    parser.add_argument('command', choices=['start', 'stop', 'reset', 'auto'], 
                       help='Command to execute')
    parser.add_argument('--duration', type=float, default=60.0,
                       help='Duration for auto recording (seconds)')
    
    args = parser.parse_args()
    
    rclpy.init()
    controller = PathErrorController()
    
    try:
        if args.command == 'start':
            print_usage()
            print("\n🚀 Starting error recording...")
            if controller.start_recording():
                print("📊 Recording started! Press Ctrl+C or use 'stop' command to finish.")
                try:
                    rclpy.spin(controller)
                except KeyboardInterrupt:
                    print("\n⏹️  Stopping recording...")
                    controller.stop_recording()
        
        elif args.command == 'stop':
            print("⏹️  Stopping error recording and generating summary...")
            controller.stop_recording()
            print("✅ Analysis complete! Check the output directory for results.")
        
        elif args.command == 'reset':
            print("🔄 Resetting accumulated error data...")
            controller.reset_data()
            print("✅ Data reset complete.")
        
        elif args.command == 'auto':
            print_usage()
            print(f"\n🤖 Starting automatic {args.duration}s recording...")
            
            if controller.start_recording():
                print(f"📊 Recording for {args.duration} seconds...")
                time.sleep(args.duration)
                print("⏹️  Stopping recording...")
                controller.stop_recording()
                print("✅ Automatic analysis complete!")
            else:
                print("❌ Failed to start recording.")
        
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
    finally:
        controller.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main() 