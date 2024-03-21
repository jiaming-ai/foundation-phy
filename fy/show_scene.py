

from fy.base import BaseTestScene



class ShowScene(BaseTestScene):
    
    def __init__(self, FLAGS) -> None:
        super().__init__(FLAGS)
    

    
    def add_objects(self):
        # add objects to the scene

        scales = [0.7, 1, 1.5, 2.5]
        for i, scale in enumerate(scales):
            x = -0.8 + i * 0.3
            
            super().add_dynamic_object(
                asset_id="Mens_ASV_Billfish_Boat_Shoe_in_Tan_Leather_wmUJ5PbwANc",
                scale=scale,
                position=[x, 0, 1], 
                velocity=[0, 0, 0])

    
        self.shift_scene([0, 5, 0])