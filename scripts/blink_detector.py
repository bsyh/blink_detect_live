#!/usr/bin/env python3

import rospy
from blink_detect_live.msg import PupilDiameter, Blink
import numpy as np




class BlinkDetector:
    def __init__(self, pupil:str, blink:str, concat_gap_interval = 5, samples2smooth = 11) -> None:
        # Initialize parameters
        self.concat_gap_interval = concat_gap_interval
        self.samples2smooth = (samples2smooth // 2) * 2 + 1

        # Initialize other variables
        self.onset = None
        self.offset = None
        self.last_monotonically_dec = None
        self.last_diameter = 0
        self.gap_count = 0
        self.diameter_buffer = []
        self.timestamp_buffer = []

        # Initialize publisher and subscriber
        self.pub = rospy.Publisher(blink, Blink, queue_size=10)
        self.blink = Blink()
        self.count = 1

        rospy.Subscriber(pupil, PupilDiameter, self.callback)

        
    
    def callback(self, data):
        # Update gap count and get current diameter
        self.gap_count += 1
        if np.isnan(data.diameter):
            temp = 0
        else:
            temp = data.diameter

        # Update buffers and get smoothed diameter
        # if buffer is not full, append data to buffer
        if self.pop_buffer(self.diameter_buffer, temp, self.samples2smooth) and self.pop_buffer(self.timestamp_buffer, rospy.Time(data.timestamp.secs,data.timestamp.nsecs),  self.samples2smooth):
            current_diameter = self.smooth(self.diameter_buffer, self.samples2smooth)
            # Detect blink
            # when diameter is zero, a blink happens
            if self.diameter_buffer[(self.samples2smooth//2)+1] == 0:
                self.last_diameter = 0
                # if self.pop_buffer(self.diameter_buffer, 0,  self.samples2smooth) and self.pop_buffer(self.timestamp_buffer, rospy.Time(data.timestamp.secs,data.timestamp.nsecs),  self.samples2smooth):
                if len(self.diameter_buffer) >= self.samples2smooth:

                    self.onset = self.last_monotonically_dec 
                    
                    
                # print()
            # valid diameter data detected
            else:

                
                # print("".join(["_" for i in range(int(current_diameter*15))]),end='')

                if self.onset is None:
                    if current_diameter-self.last_diameter > 0:
                        
                        self.last_monotonically_dec = self.timestamp_buffer[(self.samples2smooth//2)+1]
                        # print("ON",end=str(self.count))
                        
                else:
                    
                    if current_diameter-self.last_diameter >= 0 or self.offset is None:
                        self.last_diameter = current_diameter
                        self.offset = self.timestamp_buffer[(self.samples2smooth//2)+1]
                    else:

                        if self.blink.onset is None:
                            self.blink.onset = self.onset
                        self.blink.offset = self.offset
                        self.blink.duration = self.blink.offset - self.blink.onset

                        if self.gap_count > self.concat_gap_interval:
                            # Publish blink if no more blink is detected whtin concat_gap_interval samples

                            self.gap_count = 0

                            
                            self.blink.count = self.count
                            self.pub.publish(self.blink)

                            self.blink.onset, self.blink.offset = None, None
                            # print("OFF",end=str(self.count))
                            self.count+=1

                        

                        self.gap_count = 0

                        self.last_monotonically_dec = self.offset
                        
                        self.offset, self.onset = None, None

                            
                # print()
            self.last_diameter = current_diameter
                
        

    def pub(self):
        pass

    @staticmethod
    def pop_buffer(buf, element,  size):
    # Update buffer with new element and limit size
        buf.append(element)
        if len(buf) > size:
            del buf[0]
            return True
        else:
            return False

    @staticmethod
    def smooth(x, window_len):
        """
        filter series by a given window_len as convolution kernel
        """

        if window_len < 3:
            return x

        # Window length must be odd
        if window_len%2 == 0:
            window_len += 1

        w = np.ones(window_len)
        # convolve raw data. Convolution may decrease the dimension of array
        y = np.convolve(w, x, mode='valid') / len(w)


        return y
def main():
    rospy.init_node('blink_detector', anonymous=True)
    print("---------Ros init of blink_detector done---------")
    # id = rospy.get_param("/blink_detect_live/id")
    id = '1'

    pupil_left_topic = f'/humans/faces/face_{id}/eyes/left/pupildiameter'
    pupil_right_topic = f'/humans/faces/face_{id}/eyes/right/pupildiameter'
        
    blink_left_topic = f'/humans/faces/face_{id}/eyes/left/blink'
    blink_right_topic = f'/humans/faces/face_{id}/eyes/right/blink'

    concat_gap_interval = rospy.get_param("/blink_detect/concat_gap_interval")
    samples2smooth = rospy.get_param("/blink_detect/samples2smooth")


    left_dector = BlinkDetector(pupil_left_topic, blink_left_topic, concat_gap_interval, samples2smooth)
    right_dector = BlinkDetector(pupil_right_topic, blink_right_topic, concat_gap_interval, samples2smooth)


    rospy.spin()


# Definition of the main loop
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt as e:
        print('Key press: ', e)
    except rospy.ROSInterruptException as e:
        print('connection interrupt: ', e)